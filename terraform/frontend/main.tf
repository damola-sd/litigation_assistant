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

# ECR Repository for the Next.js Docker image
resource "aws_ecr_repository" "frontend" {
  name                 = "litigation-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Secrets Manager - server-side runtime secrets only.
# NEXT_PUBLIC_* vars are baked into the image at build time via Docker build args;
# they cannot be injected at runtime by App Runner.
resource "aws_secretsmanager_secret" "frontend_secrets" {
  name                    = "${var.project_name}-frontend-secrets"
  description             = "Frontend runtime secrets for Litigation Prep Assistant"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "frontend_secrets" {
  secret_id = aws_secretsmanager_secret.frontend_secrets.id
  secret_string = jsonencode({
    CLERK_SECRET_KEY = var.clerk_secret_key
  })
}

# --- IAM Roles & Policies ---

# 1. Service Role (App Runner pulls ECR image and reads secrets at startup)
resource "aws_iam_role" "apprunner_service_role" {
  name               = "${var.project_name}-frontend-apprunner-service-role"
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
  name        = "${var.project_name}-frontend-apprunner-secrets-policy"
  description = "Allows App Runner frontend service to read runtime secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["secretsmanager:GetSecretValue"]
        Effect   = "Allow"
        Resource = [aws_secretsmanager_secret.frontend_secrets.arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_secrets_access" {
  role       = aws_iam_role.apprunner_service_role.name
  policy_arn = aws_iam_policy.apprunner_secrets_policy.arn
}

# 2. Instance Role (permissions available to the running application container)
resource "aws_iam_role" "apprunner_instance_role" {
  name = "${var.project_name}-frontend-apprunner-instance-role"

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

resource "aws_iam_role_policy_attachment" "apprunner_instance_secrets_access" {
  role       = aws_iam_role.apprunner_instance_role.name
  policy_arn = aws_iam_policy.apprunner_secrets_policy.arn
}

# --- App Runner Service ---

resource "aws_apprunner_service" "frontend" {
  service_name = "litigation-frontend"

  source_configuration {
    image_repository {
      image_identifier      = "${aws_ecr_repository.frontend.repository_url}:latest"
      image_repository_type = "ECR"

      image_configuration {
        port = "3000"

        runtime_environment_variables = {
          NODE_ENV = "production"
          HOSTNAME = "0.0.0.0"
        }

        # CLERK_SECRET_KEY is server-side only — safe to inject at runtime.
        # NEXT_PUBLIC_* keys must be passed as --build-arg during `docker build`.
        runtime_environment_secrets = {
          CLERK_SECRET_KEY = "${aws_secretsmanager_secret.frontend_secrets.arn}:CLERK_SECRET_KEY::"
        }
      }
    }

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_service_role.arn
    }

    auto_deployments_enabled = true
  }

  instance_configuration {
    cpu               = "1024"
    memory            = "2048"
    instance_role_arn = aws_iam_role.apprunner_instance_role.arn
  }

  tags = {
    Project = var.project_name
  }

  depends_on = [aws_secretsmanager_secret_version.frontend_secrets]
}
