variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (staging | production)"
  type        = string
  validation {
    values = ["staging", "production"]
  }
}

variable "domain" {
  description = "Custom domain (e.g. mwalimukit.co.ke)"
  type        = string
}

variable "api_secret_key" {
  description = "FastAPI JWT secret key (min 32 chars)"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.api_secret_key) >= 32
    error_message = "api_secret_key must be at least 32 characters."
  }
}

variable "db_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.db_password) >= 16
    error_message = "db_password must be at least 16 characters."
  }
}

variable "redis_auth_token" {
  description = "Redis AUTH token (min 16 chars)"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.redis_auth_token) >= 16
    error_message = "redis_auth_token must be at least 16 characters."
  }
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.medium"
}

variable "redis_instance_class" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.micro"
}

variable "api_cpu" {
  description = "CPU units for Fargate API task"
  type        = string
  default     = "1024"
}

variable "api_memory" {
  description = "Memory (MB) for Fargate API task"
  type        = string
  default     = "2048"
}

variable "web_cpu" {
  description = "CPU units for Fargate Web task"
  type        = string
  default     = "256"
}

variable "web_memory" {
  description = "Memory (MB) for Fargate Web task"
  type        = string
  default     = "512"
}

variable "api_desired_count" {
  description = "Desired API task count (min running)"
  type        = number
  default     = 2
}

variable "web_desired_count" {
  description = "Desired Web task count"
  type        = number
  default     = 2
}

variable "sentry_dsn" {
  description = "Sentry DSN (optional)"
  type        = string
  default     = ""
}

variable "stripe_secret_key" {
  description = "Stripe secret key (optional)"
  type        = string
  default     = ""
  sensitive   = true
}
