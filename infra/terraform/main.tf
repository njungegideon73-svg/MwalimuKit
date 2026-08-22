# ─────────────────────────────────────────────────────────────
# MwalimuKit — Terraform infrastructure (AWS reference)
# ─────────────────────────────────────────────────────────────
# Provisions the cloud foundation: VPC, RDS (Multi-AZ),
# ElastiCache Redis, ECS/Fargate services, and an ALB.
#
# This mirrors the Docker Compose production stack but uses
# managed cloud services for production-grade availability.
#
# Usage:
#   cd infra/terraform
#   terraform init
#   terraform plan -var="environment=production" -var="domain=mwalimukit.co.ke"
#   terraform apply -var="environment=production" -var="domain=mwalimukit.co.ke"
#
# Required variables:
#   - aws_region
#   - environment (staging | production)
#   - domain
#   - api_secret_key
#   - db_password
#   - stripe_secret_key (optional)
#   - sentry_dsn (optional)
# ─────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    bucket         = "mwalimukit-terraform-state"
    key            = "mwalimukit/terraform.tfstate"
    region         = var.aws_region
    encrypt        = true
    dynamodb_table = "mwalimukit-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
}

# ─────────────────────────────────────────────────────────────
# VPC
# ─────────────────────────────────────────────────────────────
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "mwalimukit-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = slice(data.aws_availability_zones.available.names, 0, 2)
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = false
  nat_gateway_tags       = { Name = "mwalimukit-${var.environment}-natgw" }

  enable_dns_hostnames = true
  enable_dns_support   = true
  enable_flow_log      = true

  tags = local.common_tags
}

data "aws_availability_zones" "available" {}

# ─────────────────────────────────────────────────────────────
# RDS Postgres (Multi-AZ, encrypted, automated backups)
# ─────────────────────────────────────────────────────────────
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier     = "mwalimukit-${var.environment}"
  engine         = "postgres"
  engine_version = "16"
  engine_mode    = "provisioned"

  instance_class    = var.db_instance_class
  allocated_storage = 20
  max_allocated_storage = 200
  storage_encrypted = true

  db_name  = "mwalimukit"
  username = "mwalimu"
  port     = 5432

  multi_az               = true
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 14
  backup_window           = "02:00-03:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  apply_immediately       = false
  skip_final_snapshot     = false
  final_snapshot_identifier = "mwalimukit-${var.environment}-final-${formatdate("YYYYMMDDHHmmss", timestamp())}"

  deletion_protection      = var.environment == "production"
  copy_tags_to_snapshot    = true

  tags = local.common_tags
}

resource "aws_security_group" "rds" {
  name        = "mwalimukit-${var.environment}-rds"
  description = "RDS access from ECS"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

# ── RDS parameter group for RLS / performance ────────────────
resource "aws_db_parameter_group" "rds" {
  name   = "mwalimukit-${var.environment}-postgres"
  family = "postgres16"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }
}

# ─────────────────────────────────────────────────────────────
# ElastiCache Redis (for rate limiting + response cache)
# ─────────────────────────────────────────────────────────────
module "redis" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "~> 9.0"

  cluster_id         = "mwalimukit-${var.environment}"
  engine             = "redis"
  node_type          = var.redis_instance_class
  num_cache_nodes    = 1
  port               = 6379
  apply_immediately  = false
  family             = "redis7"

  subnet_group_name  = module.vpc.elasticache_subnet_group_name
  security_group_ids = [aws_security_group.redis.id]

  transit_encryption_enabled = true
  auth_token                 = var.redis_auth_token

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = local.common_tags
}

resource "aws_security_group" "redis" {
  name        = "mwalimukit-${var.environment}-redis"
  description = "Redis access from ECS"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }

  tags = local.common_tags
}

# ─────────────────────────────────────────────────────────────
# Application Load Balancer
# ─────────────────────────────────────────────────────────────
module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "~> 9.0"

  name               = "mwalimukit-${var.environment}"
  load_balancer_type = "application"
  vpc_id             = module.vpc.vpc_id
  subnets            = module.vpc.public_subnets
  security_groups    = [aws_security_group.alb.id]

  enable_deletion_protection = var.environment == "production"

  tags = local.common_tags
}

resource "aws_security_group" "alb" {
  name        = "mwalimukit-${var.environment}-alb"
  description = "ALB ingress/egress"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_lb_target_group" "api" {
  name        = "mwalimukit-api-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  health_check {
    path                = "/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }
}

resource "aws_lb_target_group" "web" {
  name        = "mwalimukit-web-${var.environment}"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  health_check {
    path                = "/"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = module.alb.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      protocol = "HTTPS"
      port     = "443"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = module.alb.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021"
  certificate_arn   = aws_acm_certificate.api.arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ── Route 53 / certificate ─────────────────────────────────
data "aws_route53_zone" "selected" {
  name         = var.domain
  private_zone = false
}

resource "aws_acm_certificate" "api" {
  domain_name       = var.domain
  subject_alternative_names = ["*.${var.domain}"]
  validation_method = "DNS"
  lifecycle {
    create_before_destroy = true
  }
  tags = local.common_tags
}

# ─────────────────────────────────────────────────────────────
# ECS / Fargate
# ─────────────────────────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = "mwalimukit-${var.environment}"
  tags = local.common_tags
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name
  capacity_providers {
    capacity_provider_name = "FARGATE"
    base                   = 1
    weight                 = 1
  }
  capacity_providers {
    capacity_provider_name = "FARGATE_SPOT"
    base                   = 0
    weight                 = 1
  }
}

# ── ECR repositories ─────────────────────────────────────────
resource "aws_ecr_repository" "api" {
  name = "mwalimukit-api"
  image_scanning_configuration {
    scan_on_push = true
  }
  lifecycle_policy {
    policy = jsonencode({
      rules = [{
        ruleAction = { mode = "EXPIRE" }
        count      = { type = "sinceImageLastPushed", value = 30 }
        countUnit  = "days"
      }]
    })
  }
  tags = local.common_tags
}

resource "aws_ecr_repository" "web" {
  name = "mwalimukit-web"
  image_scanning_configuration {
    scan_on_push = true
  }
  lifecycle_policy {
    policy = jsonencode({
      rules = [{
        ruleAction = { mode = "EXPIRE" }
        count      = { type = "sinceImageLastPushed", value = 30 }
        countUnit  = "days"
      }]
    })
  }
  tags = local.common_tags
}

# ── Task definitions ───────────────────────────────────────
resource "aws_ecs_task_definition" "api" {
  family                   = "mwalimukit-api-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_exec.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "api"
    image = "${aws_ecr_repository.api.repository_url}:latest"
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "API_ENV",          value = var.environment },
      { name = "DATABASE_URL",     value = "postgresql+asyncpg://mwalimu:${var.db_password}@${module.rds.endpoint}:5432/mwalimukit" },
      { name = "REDIS_URL",        value = "rediss://:${var.redis_auth_token}@${module.redis.configuration_endpoint}:6379" },
      { name = "API_CORS_ORIGINS", value = "[\"https://${var.domain}\"]" },
      { name = "SENTRY_DSN",        value = var.sentry_dsn },
    ]
    secrets = [
      { name = "API_SECRET_KEY", value = aws_secretsmanager_secret.api_secret.arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = "/ecs/mwalimukit-api-${var.environment}"
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ecs"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = local.common_tags
}

resource "aws_ecs_task_definition" "web" {
  family                   = "mwalimukit-web-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.web_cpu
  memory                   = var.web_memory
  execution_role_arn       = aws_iam_role.ecs_exec.arn

  container_definitions = jsonencode([{
    name  = "web"
    image = "${aws_ecr_repository.web.repository_url}:latest"
    portMappings = [{ containerPort = 80, protocol = "tcp" }]
    environment = [
      { name = "VITE_API_BASE_URL", value = "https://${var.domain}/api/v1" },
      { name = "VITE_APP_NAME",     value = "MwalimuKit" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = "/ecs/mwalimukit-web-${var.environment}"
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ecs"
      }
    }
  }])

  tags = local.common_tags
}

# ── ECS services ────────────────────────────────────────────
resource "aws_ecs_service" "api" {
  name            = "mwalimukit-api-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  deployment_controller {
    type = "CODE_DEPLOY"
  }

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = local.common_tags
}

resource "aws_ecs_service" "web" {
  name            = "mwalimukit-web-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.web_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 80
  }

  tags = local.common_tags
}

resource "aws_security_group" "ecs" {
  name        = "mwalimukit-${var.environment}-ecs"
  description = "ECS Fargate ingress from ALB"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

# ── IAM roles ───────────────────────────────────────────────
resource "aws_iam_role" "ecs_exec" {
  name = "mwalimukit-ecs-exec-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_exec" {
  role       = aws_iam_role.ecs_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "mwalimukit-ecs-task-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_secrets" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}

# ── Secrets Manager ─────────────────────────────────────────
resource "aws_secretsmanager_secret" "api_secret" {
  name = "mwalimukit-api-secret-${var.environment}"
  description = "FastAPI JWT secret key"
  recovery_window_in_days = 30
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "api_secret" {
  secret_id     = aws_secretsmanager_secret.api_secret.id
  secret_string = var.api_secret_key
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "mwalimukit-db-password-${var.environment}"
  description = "PostgreSQL password"
  recovery_window_in_days = 30
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

# ── S3 for object storage (PDF exports, etc.) ──────────────
resource "aws_s3_bucket" "storage" {
  bucket = "mwalimukit-storage-${var.environment}"
  tags = local.common_tags
}

resource "aws_s3_bucket_versioning" "storage" {
  bucket = aws_s3_bucket.storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id
  rule {
    id     = "expire-temp"
    status = "Enabled"
    expiration {
      days = 365
    }
  }
}

# ── CloudWatch ──────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "api" {
  name = "/ecs/mwalimukit-api-${var.environment}"
  retention_in_days = 90
  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "web" {
  name = "/ecs/mwalimukit-web-${var.environment}"
  retention_in_days = 90
  tags = local.common_tags
}

# ── SNS for alerts ──────────────────────────────────────────
resource "aws_sns_topic" "alerts" {
  name = "mwalimukit-alerts-${var.environment}"
  tags = local.common_tags
}

# ── Common tags ─────────────────────────────────────────────
locals {
  common_tags = {
    Project     = "mwalimukit"
    Environment = var.environment
  }
}
