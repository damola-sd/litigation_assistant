# Infrastructure & Deployment Guide

This guide covers provisioning all AWS infrastructure with Terraform and deploying Docker images for the database, backend, and frontend.

## Architecture

```
AWS App Runner (Frontend: Next.js)
        ↓ HTTP
AWS App Runner (Backend: FastAPI)
        ↓ asyncpg
AWS Aurora Serverless v2 (PostgreSQL)
```

All three modules live under `terraform/` and are managed independently.

## Prerequisites

- AWS CLI configured (`aws configure`) with credentials for account `224310271100`, region `eu-west-1`
- Terraform >= 1.0 installed
- Docker with buildx support (for `--platform linux/amd64`)
- AWS account with permissions for: ECR, App Runner, RDS, Secrets Manager, IAM

---

## The Dependency Problem

There is a **circular dependency** between the backend and frontend:

| Service  | Needs at deploy time | Source |
|----------|----------------------|--------|
| Backend  | `allowed_origins` (frontend URL) | Created after frontend deploy |
| Frontend | `NEXT_PUBLIC_API_URL` (backend URL) | Created after backend deploy |

**Resolution strategy:**
1. Deploy backend first with a wildcard `allowed_origins = "*"` placeholder
2. Get the backend URL → deploy frontend
3. Get the frontend URL → update backend `allowed_origins` and re-apply

---

## terraform.tfvars Reference

Fill in these files before running `terraform apply`. Never commit real secrets.

### `terraform/database/terraform.tfvars`

```hcl
aws_region   = "eu-west-1"
min_capacity = 0.5   # 0.5 ACU minimum (~$43/month when idle)
max_capacity = 1.0   # Scale up to 1 ACU under load
```

### `terraform/backend/terraform.tfvars`

```hcl
aws_region     = "eu-west-1"
openai_api_key = "sk-proj-<your-openai-key>"
openai_model   = "gpt-4o"
clerk_jwks_url = "https://<your-clerk-instance>.clerk.accounts.dev/.well-known/jwks.json"
clerk_issuer   = "https://<your-clerk-instance>.clerk.accounts.dev"

# Step 1: use wildcard; Step 4: replace with real frontend URL
allowed_origins = "*"
# allowed_origins = "https://<random-id>.eu-west-1.awsapprunner.com"
```

### `terraform/frontend/terraform.tfvars`

```hcl
aws_region                        = "eu-west-1"
clerk_secret_key                  = "sk_test_<your-clerk-secret-key>"
next_public_clerk_publishable_key = "pk_test_<your-clerk-publishable-key>"

# Fill in after backend is deployed (Step 2c)
next_public_api_url = "https://<random-id>.eu-west-1.awsapprunner.com"
```

---

## Deployment Steps

### Step 1 — Deploy the Database

The database has no dependencies on other services.

```bash
cd terraform/database

terraform init
terraform apply
```

Note the outputs — you'll need the secret ARN when the backend reads DB credentials:

```bash
terraform output aurora_secret_arn
terraform output aurora_cluster_endpoint
```

---

### Step 2 — Deploy the Backend

#### 2a. Create the ECR repository only

App Runner needs an image in ECR before the service can be created. Provision ECR first.

```bash
cd terraform/backend

terraform init
terraform apply -target=aws_ecr_repository.backend
```

Capture the ECR URL:

```bash
export BACKEND_ECR_URL=$(terraform output -raw ecr_repository_url)
echo $BACKEND_ECR_URL
# e.g. 224310271100.dkr.ecr.eu-west-1.amazonaws.com/litigation-backend
```

#### 2b. Build and push the backend image

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region eu-west-1 \
  | docker login --username AWS --password-stdin $BACKEND_ECR_URL

# Build for linux/amd64 (required for App Runner)
cd ../../backend
docker build --platform linux/amd64 -t litigation-backend .

# Tag with the full ECR URL (required — Docker push needs the registry in the image name)
docker tag litigation-backend:latest $BACKEND_ECR_URL:latest

# Push
docker push $BACKEND_ECR_URL:latest
```

#### 2c. Deploy the full backend infrastructure

Make sure `terraform/backend/terraform.tfvars` has `allowed_origins = "*"` for now.

```bash
cd ../terraform/backend
terraform apply
```

Capture the backend URL — you need this for the frontend:

```bash
export BACKEND_URL=$(terraform output -raw app_runner_url)
echo $BACKEND_URL
# e.g. https://j7psf2vecm.eu-west-1.awsapprunner.com
```

---

### Step 3 — Deploy the Frontend

#### 3a. Create the ECR repository only

```bash
cd ../frontend   # i.e. terraform/frontend

terraform init
terraform apply -target=aws_ecr_repository.frontend
```

Capture the ECR URL:

```bash
export FRONTEND_ECR_URL=$(terraform output -raw ecr_repository_url)
echo $FRONTEND_ECR_URL
# e.g. 224310271100.dkr.ecr.eu-west-1.amazonaws.com/litigation-frontend
```

#### 3b. Build and push the frontend image

`NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` are **baked into the image at build time** — they cannot be changed without rebuilding.

```bash
# Set build-time variables — BACKEND_URL already includes https://
export NEXT_PUBLIC_API_URL=$BACKEND_URL
export CLERK_PUBLISHABLE_KEY="pk_test_<your-clerk-publishable-key>"

# Authenticate Docker to ECR
aws ecr get-login-password --region eu-west-1 \
  | docker login --username AWS --password-stdin $FRONTEND_ECR_URL

# Build with build args
cd ../../frontend
docker build \
  --build-arg NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY \
  --platform linux/amd64 \
  -t litigation-frontend .

# Tag with the full ECR URL
docker tag litigation-frontend:latest $FRONTEND_ECR_URL:latest

# Push
docker push $FRONTEND_ECR_URL:latest
```

#### 3c. Deploy the full frontend infrastructure

Update `terraform/frontend/terraform.tfvars` with the real backend URL, then apply:

```bash
cd ../terraform/frontend
terraform apply
```

Capture the frontend URL:

```bash
export FRONTEND_URL=$(terraform output -raw app_runner_url)
echo $FRONTEND_URL
# e.g. https://qntnj7pdpw.eu-west-1.awsapprunner.com
```

---

### Step 4 — Fix Backend CORS

Now that the frontend URL is known, update the backend `allowed_origins` and re-apply.

Edit `terraform/backend/terraform.tfvars` — paste `$FRONTEND_URL` directly, it already includes `https://`:

```hcl
allowed_origins = "https://<random-id>.eu-west-1.awsapprunner.com"
```

Apply the change:

```bash
cd terraform/backend
terraform apply
```

This updates the secret in Secrets Manager. App Runner will pick it up on the next service restart or deployment.

---

## Re-deploying After Code Changes

When you push new code, rebuild and push the image. App Runner with auto-deployment enabled will detect the new image and redeploy.

**Backend:**

```bash
cd backend
docker build --platform linux/amd64 -t litigation-backend .
docker tag litigation-backend:latest $BACKEND_ECR_URL:latest
docker push $BACKEND_ECR_URL:latest
```

**Frontend** (rebuild required whenever `NEXT_PUBLIC_*` values change):

```bash
cd frontend
docker build \
  --build-arg NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY \
  --platform linux/amd64 \
  -t litigation-frontend .
docker tag litigation-frontend:latest $FRONTEND_ECR_URL:latest
docker push $FRONTEND_ECR_URL:latest
```

If the ECR URL variables are not set in your shell, recapture them:

```bash
export BACKEND_ECR_URL=$(cd terraform/backend && terraform output -raw ecr_repository_url)
export FRONTEND_ECR_URL=$(cd terraform/frontend && terraform output -raw ecr_repository_url)
```

---

## Teardown / Destroy

Destroy in reverse order to avoid dependency errors. The database should be last.

```bash
# 1. Destroy frontend (no downstream dependencies)
cd terraform/frontend
terraform destroy

# 2. Destroy backend
cd ../backend
terraform destroy

# 3. Destroy database (last — other services depended on it)
cd ../database
terraform destroy
```

> **Note:** Aurora Serverless v2 has `skip_final_snapshot = true` in the current config, so the cluster is deleted without a final backup. Change this before running destroy in production if you need a snapshot.

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `terraform init` | Download providers (run once per module) |
| `terraform plan` | Preview changes without applying |
| `terraform apply` | Create/update infrastructure |
| `terraform apply -target=aws_ecr_repository.backend` | Create only the ECR repo |
| `terraform output -raw ecr_repository_url` | Get ECR push URL |
| `terraform output -raw app_runner_url` | Get deployed service URL |
| `terraform destroy` | Tear down all resources in a module |
