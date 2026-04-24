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

variable "pinecone_api_key" {
  description = "Pinecone API key for RAG (optional; leave empty to disable vector retrieval)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "pinecone_index_host" {
  description = "Pinecone serverless index host URL from the console (preferred over index name)"
  type        = string
  sensitive   = false
  default     = ""
}

variable "pinecone_index_name" {
  description = "Pinecone index name if host is not used"
  type        = string
  sensitive   = false
  default     = ""
}

variable "pinecone_namespace" {
  description = "Optional Pinecone namespace for isolating vectors in the index"
  type        = string
  sensitive   = false
  default     = ""
}