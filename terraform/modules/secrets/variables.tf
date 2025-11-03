# Secrets Module Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
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

variable "polygon_api_key" {
  description = "Polygon.io API key for market data"
  type        = string
  sensitive   = true
  default     = ""
}

variable "create_database_secret" {
  description = "Whether to create database secret (for future use)"
  type        = bool
  default     = false
}
