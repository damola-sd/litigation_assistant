#!/usr/bin/env bash
set -euo pipefail

REGION="eu-west-1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TERRAFORM_FRONTEND_DIR="$SCRIPT_DIR/../terraform/frontend"
TERRAFORM_BACKEND_DIR="$SCRIPT_DIR/../terraform/backend"
FRONTEND_DIR="$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Resolve ECR URL
# ---------------------------------------------------------------------------
if [[ -z "${FRONTEND_ECR_URL:-}" ]]; then
  echo "FRONTEND_ECR_URL not set — fetching from Terraform state..."
  FRONTEND_ECR_URL=$(cd "$TERRAFORM_FRONTEND_DIR" && terraform output -raw ecr_repository_url)
fi
echo "ECR: $FRONTEND_ECR_URL"

# ---------------------------------------------------------------------------
# Resolve build-time env vars
# ---------------------------------------------------------------------------
if [[ -z "${NEXT_PUBLIC_API_URL:-}" ]]; then
  echo "NEXT_PUBLIC_API_URL not set — fetching backend URL from Terraform state..."
  NEXT_PUBLIC_API_URL=$(cd "$TERRAFORM_BACKEND_DIR" && terraform output -raw app_runner_url)
fi
echo "API URL: $NEXT_PUBLIC_API_URL"

if [[ -z "${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:-}" ]]; then
  ENV_LOCAL="$FRONTEND_DIR/.env.local"
  if [[ -f "$ENV_LOCAL" ]]; then
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$(grep -E '^NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=' "$ENV_LOCAL" | cut -d '=' -f2-)
    echo "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY read from .env.local"
  fi
fi

if [[ -z "${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:-}" ]]; then
  echo ""
  echo "ERROR: NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is not set and was not found in .env.local."
  echo "  Export it before running: export NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_..."
  exit 1
fi

# ---------------------------------------------------------------------------
# Authenticate Docker to ECR
# ---------------------------------------------------------------------------
echo ""
echo "Authenticating Docker to ECR..."
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$FRONTEND_ECR_URL"

# ---------------------------------------------------------------------------
# Build, tag, push
# ---------------------------------------------------------------------------
echo ""
echo "Building frontend image..."
docker build \
  --build-arg NEXT_PUBLIC_API_URL="$NEXT_PUBLIC_API_URL" \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" \
  --platform linux/amd64 \
  -t litigation-frontend \
  "$FRONTEND_DIR"

echo ""
echo "Tagging and pushing..."
docker tag litigation-frontend:latest "$FRONTEND_ECR_URL:latest"
docker push "$FRONTEND_ECR_URL:latest"

echo ""
echo "Done. App Runner will pick up the new image and redeploy automatically."
