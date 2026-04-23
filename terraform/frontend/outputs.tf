output "app_runner_url" {
  description = "The URL of the frontend App Runner service"
  value       = "https://${aws_apprunner_service.frontend.service_url}"
}

output "ecr_repository_url" {
  description = "The ECR repository URL — use this as the push target in CI/CD"
  value       = aws_ecr_repository.frontend.repository_url
}

output "secrets_arn" {
  description = "The ARN of the Secrets Manager secret holding frontend runtime secrets"
  value       = aws_secretsmanager_secret.frontend_secrets.arn
}
