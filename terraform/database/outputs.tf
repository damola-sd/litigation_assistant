output "aurora_cluster_arn" {
  description = "ARN of the Aurora cluster"
  value       = aws_rds_cluster.aurora.arn
}

output "aurora_cluster_endpoint" {
  description = "Writer endpoint for the Aurora cluster"
  value       = aws_rds_cluster.aurora.endpoint
}

output "aurora_secret_arn" {
  description = "ARN of the Secrets Manager secret containing database credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "database_name" {
  description = "Name of the database"
  value       = aws_rds_cluster.aurora.database_name
}


output "data_api_enabled" {
  description = "Status of Data API"
  value       = aws_rds_cluster.aurora.enable_http_endpoint ? "Enabled" : "Disabled"
}

output "setup_instructions" {
  description = "Instructions for setting up the database"
  value = <<-EOT
    
    ✅ Aurora Serverless v2 cluster deployed successfully!
    
    Database Details:
    - Cluster: ${aws_rds_cluster.aurora.cluster_identifier}
    - Database: ${aws_rds_cluster.aurora.database_name}
  EOT
}