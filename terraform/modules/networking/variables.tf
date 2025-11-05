# Networking Module Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for regional resources"
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

variable "backend_service_name" {
  description = "Name of the backend Cloud Run service"
  type        = string
}

variable "api_domain" {
  description = "Custom domain for the API (e.g., api.goingmerry-stonks.com)"
  type        = string
  default     = ""
}

variable "enable_ssl" {
  description = "Enable SSL certificate and HTTPS"
  type        = bool
  default     = true
}

variable "enable_cloud_armor" {
  description = "Enable Cloud Armor security policy"
  type        = bool
  default     = true
}

variable "rate_limit_requests" {
  description = "Maximum requests per minute per IP for rate limiting"
  type        = number
  default     = 100
}

variable "blocked_countries" {
  description = "List of country codes to block (ISO 3166-1 alpha-2)"
  type        = list(string)
  default     = []
}

variable "log_sample_rate" {
  description = "Sample rate for load balancer logs (0.0 to 1.0)"
  type        = number
  default     = 1.0
}

variable "frontend_bucket_name" {
  description = "Cloud Storage bucket name for frontend static files"
  type        = string
  default     = ""
}
