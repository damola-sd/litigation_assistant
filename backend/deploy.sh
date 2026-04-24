#!/usr/bin/env bash
set -euo pipefail

REGION="eu-west-1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TERRAFORM_BACKEND_DIR="$SCRIPT_DIR/../terraform/backend"
BACKEND_DIR="$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Resolve ECR URL
# ---------------------------------------------------------------------------
if [[ -z "${BACKEND_ECR_URL:-}" ]]; then
  echo "BACKEND_ECR_URL not set — fetching from Terraform state..."
  BACKEND_ECR_URL=$(cd "$TERRAFORM_BACKEND_DIR" && terraform output -raw ecr_repository_url)
fi
echo "ECR: $BACKEND_ECR_URL"

# ---------------------------------------------------------------------------
# Authenticate Docker to ECR
# ---------------------------------------------------------------------------
echo ""
echo "Authenticating Docker to ECR..."
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$BACKEND_ECR_URL"

# ---------------------------------------------------------------------------
# Build, tag, push
# ---------------------------------------------------------------------------
echo ""
echo "Building backend image..."
docker build \
  --platform linux/amd64 \
  -t litigation-backend \
  "$BACKEND_DIR"

echo ""
echo "Tagging and pushing..."
docker tag litigation-backend:latest "$BACKEND_ECR_URL:latest"
docker push "$BACKEND_ECR_URL:latest"

echo ""
echo "Done. App Runner will pick up the new image and redeploy automatically."
