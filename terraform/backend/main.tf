terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ECR Repository for Docker Images
resource "aws_ecr_repository" "backend" {
  name                 = "litigation-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Data source to find the Aurora database secret
data "aws_secretsmanager_secret" "db_creds" {
  name = "litigation-aurora-credentials"
  
  depends_on = [aws_ecr_repository.backend] # Just a soft hint for ordering
}

# Secrets Manager Setup
resource "aws_secretsmanager_secret" "backend_secrets" {
  name        = "${var.project_name}-backend-secrets-2"
  description = "Backend environment variables for Litigation Prep Assistant"
  recovery_window_in_days = 0 # Set to 0 for easier dev cleanup, use default for production
}

resource "aws_secretsmanager_secret_version" "backend_secrets" {
  secret_id     = aws_secretsmanager_secret.backend_secrets.id
  secret_string = jsonencode({
    OPENAI_API_KEY       = var.openai_api_key
    OPENROUTER_API_KEY   = var.openrouter_api_key
    MODEL                = var.openai_model
    CLERK_JWKS_URL       = var.clerk_jwks_url
    CLERK_ISSUER         = var.clerk_issuer
    ALLOWED_ORIGINS      = var.allowed_origins
    PINECONE_API_KEY     = var.pinecone_api_key
    PINECONE_INDEX_HOST  = var.pinecone_index_host
    PINECONE_INDEX_NAME  = var.pinecone_index_name
    PINECONE_NAMESPACE   = var.pinecone_namespace
    LANGFUSE_PUBLIC_KEY  = var.langfuse_public_key
    LANGFUSE_SECRET_KEY  = var.langfuse_secret_key
    LANGFUSE_HOST        = var.langfuse_host
  })
}

# --- IAM Roles & Policies ---

# 1. Access Role (Permissions for App Runner to pull image and read secrets)
resource "aws_iam_role" "apprunner_service_role" {
  name = "${var.project_name}-apprunner-service-role"
  assume_role_policy = data.aws_iam_policy_document.apprunner_service_assume_role.json
}

data "aws_iam_policy_document" "apprunner_service_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com", "tasks.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_iam_policy" "apprunner_secrets_policy" {
  name        = "${var.project_name}-apprunner-secrets-policy"
  description = "Allows App Runner to fetch secrets for environment variables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["secretsmanager:GetSecretValue"]
        Effect   = "Allow"
        Resource = [
          aws_secretsmanager_secret.backend_secrets.arn,
          data.aws_secretsmanager_secret.db_creds.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_secrets_access" {
  role       = aws_iam_role.apprunner_service_role.name
  policy_arn = aws_iam_policy.apprunner_secrets_policy.arn
}

resource "aws_iam_role_policy_attachment" "apprunner_instance_secrets_access" {
  role       = aws_iam_role.apprunner_instance_role.name
  policy_arn = aws_iam_policy.apprunner_secrets_policy.arn
}

# 2. Instance Role (Permissions for the application code at runtime)
resource "aws_iam_role" "apprunner_instance_role" {
  name = "${var.project_name}-apprunner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

# --- App Runner Service ---

resource "aws_apprunner_service" "backend" {
  service_name = "litigation-backend"

  source_configuration {
    image_repository {
      image_identifier      = "${aws_ecr_repository.backend.repository_url}:latest"
      image_repository_type = "ECR"
      
      image_configuration {
        port = "8000"
        
        runtime_environment_variables = {
          APP_ENV = "production"
        }

        # Inject secrets from Secrets Manager into Environment Variables
        runtime_environment_secrets = {
          OPENAI_API_KEY           = "${aws_secretsmanager_secret.backend_secrets.arn}:OPENAI_API_KEY::"
          MODEL                    = "${aws_secretsmanager_secret.backend_secrets.arn}:MODEL::"
          OPENROUTER_API_KEY       = "${aws_secretsmanager_secret.backend_secrets.arn}:OPENROUTER_API_KEY::"
          # Get DATABASE_URL from the 'db_url' key in the database secret
          DATABASE_URL             = "${data.aws_secretsmanager_secret.db_creds.arn}:db_url::"
          CLERK_JWKS_URL           = "${aws_secretsmanager_secret.backend_secrets.arn}:CLERK_JWKS_URL::"
          CLERK_ISSUER             = "${aws_secretsmanager_secret.backend_secrets.arn}:CLERK_ISSUER::"
          ALLOWED_ORIGINS          = "${aws_secretsmanager_secret.backend_secrets.arn}:ALLOWED_ORIGINS::"
          PINECONE_API_KEY         = "${aws_secretsmanager_secret.backend_secrets.arn}:PINECONE_API_KEY::"
          PINECONE_INDEX_HOST      = "${aws_secretsmanager_secret.backend_secrets.arn}:PINECONE_INDEX_HOST::"
          PINECONE_INDEX_NAME      = "${aws_secretsmanager_secret.backend_secrets.arn}:PINECONE_INDEX_NAME::"
          PINECONE_NAMESPACE       = "${aws_secretsmanager_secret.backend_secrets.arn}:PINECONE_NAMESPACE::"
          LANGFUSE_PUBLIC_KEY      = "${aws_secretsmanager_secret.backend_secrets.arn}:LANGFUSE_PUBLIC_KEY::"
          LANGFUSE_SECRET_KEY      = "${aws_secretsmanager_secret.backend_secrets.arn}:LANGFUSE_SECRET_KEY::"
          LANGFUSE_HOST            = "${aws_secretsmanager_secret.backend_secrets.arn}:LANGFUSE_HOST::"
        }
      }
    }
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_service_role.arn
    }
    auto_deployments_enabled = true
  }

  instance_configuration {
    cpu    = "1024"
    memory = "2048"
    instance_role_arn = aws_iam_role.apprunner_instance_role.arn
  }

  tags = {
    Project = var.project_name
  }

  depends_on = [aws_secretsmanager_secret_version.backend_secrets]
}