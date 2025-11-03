# Backend Module Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run deployment"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (e.g., prod, staging)"
  type        = string
}

variable "application_name" {
  description = "Application name for labeling"
  type        = string
  default     = "goingmerry-stonks"
}

variable "backend_image" {
  description = "Docker image for backend API (full path including tag)"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder
}

variable "polygon_api_key_secret_name" {
  description = "Full resource name of Polygon API key secret in Secret Manager"
  type        = string
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "cpu_limit" {
  description = "CPU limit for each instance"
  type        = string
  default     = "2"
}

variable "memory_limit" {
  description = "Memory limit for each instance"
  type        = string
  default     = "1Gi"
}

variable "allow_public_access" {
  description = "Whether to allow public unauthenticated access"
  type        = bool
  default     = false
}

variable "load_balancer_service_account" {
  description = "Service account email for load balancer to invoke Cloud Run"
  type        = string
  default     = ""
}

variable "vpc_connector_name" {
  description = "VPC connector for private resource access (optional)"
  type        = string
  default     = ""
}
