variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Project name for tagging and naming"
  type        = string
  default     = "litigation-prep-assistant"
}

variable "openai_api_key" {
  description = "OpenAI API Key"
  type        = string
  sensitive   = true
}

variable "openai_model" {
  description = "OpenAI Model to use"
  type        = string
  default     = "gpt-4o"
}

variable "clerk_jwks_url" {
  description = "Clerk JWKS URL for JWT validation"
  type        = string
}

variable "clerk_issuer" {
  description = "Clerk Issuer URL"
  type        = string
}

variable "allowed_origins" {
  description = "Comma-separated list of allowed CORS origins"
  type        = string
}