output "alb_dns_name" {
  description = "The DNS name of the production ALB"
  value       = module.alb.dns_name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.redis.configuration_endpoint
  sensitive   = true
}

output "api_image_url" {
  description = "ECR repository URL for the API image"
  value       = aws_ecr_repository.api.repository_url
}

output "web_image_url" {
  description = "ECR repository URL for the Web image"
  value       = aws_ecr_repository.web.repository_url
}

output "s3_storage_bucket" {
  description = "S3 bucket for object storage"
  value       = aws_s3_bucket.storage.id
}

output "alerts_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}
