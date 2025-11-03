# Database Module Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud SQL instance"
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

variable "database_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "database_tier" {
  description = "Machine type for the database instance"
  type        = string
  default     = "db-custom-2-8192" # 2 vCPU, 8GB RAM
}

variable "database_name" {
  description = "Name of the application database"
  type        = string
  default     = "goingmerry_stonks"
}

variable "database_user" {
  description = "Username for database access"
  type        = string
  default     = "app_user"
}

variable "disk_size_gb" {
  description = "Initial disk size in GB"
  type        = number
  default     = 20
}

variable "max_disk_size_gb" {
  description = "Maximum disk size for autoresize in GB"
  type        = number
  default     = 100
}

variable "high_availability" {
  description = "Enable high availability (regional instance)"
  type        = bool
  default     = true
}

variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery (requires transaction logs)"
  type        = bool
  default     = true
}

variable "max_connections" {
  description = "Maximum number of concurrent connections"
  type        = string
  default     = "100"
}

variable "vpc_network_id" {
  description = "VPC network ID for private IP (optional, uses default if not provided)"
  type        = string
  default     = ""
}

variable "authorized_networks" {
  description = "List of authorized networks for public access"
  type = list(object({
    name = string
    cidr = string
  }))
  default = []
}
