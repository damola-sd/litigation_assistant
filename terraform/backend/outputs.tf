output "app_runner_url" {
  description = "The URL of the App Runner service"
  value       = "https://${aws_apprunner_service.backend.service_url}"
}

output "ecr_repository_url" {
  description = "The URL of the ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "secrets_arn" {
  description = "The ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.backend_secrets.arn
}

output "db_creds_secret_arn" {
  description = "The ARN of the Secrets Manager secret for database credentials"
  value       = data.aws_secretsmanager_secret.db_creds.arn
}