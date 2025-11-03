# Production Environment Variables
# Architecture: Cloud Run (Backend) + Firebase Hosting (Frontend) + Cloud SQL (Database)

# ========================================
# Project Configuration
# ========================================

variable "project_id" {
  description = "GCP Project ID for production environment"
  type        = string
}

variable "region" {
  description = "Primary GCP region for resources"
  type        = string
  default     = "us-east5"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "application_name" {
  description = "Application name for resource labeling"
  type        = string
  default     = "goingmerry-stonks"
}

# ========================================
# Secrets
# ========================================

variable "polygon_api_key" {
  description = "Polygon.io API key for market data access"
  type        = string
  sensitive   = true
}

# ========================================
# Backend Configuration
# ========================================

variable "backend_image" {
  description = "Full Docker image path for backend API"
  type        = string
}

variable "backend_min_instances" {
  description = "Minimum number of backend instances"
  type        = number
  default     = 1
}

variable "backend_max_instances" {
  description = "Maximum number of backend instances"
  type        = number
  default     = 10
}

variable "backend_cpu_limit" {
  description = "CPU limit per backend instance"
  type        = string
  default     = "2"
}

variable "backend_memory_limit" {
  description = "Memory limit per backend instance"
  type        = string
  default     = "1Gi"
}

# ========================================
# Database Configuration
# ========================================

variable "database_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "database_tier" {
  description = "Machine type for database instance"
  type        = string
  default     = "db-custom-2-8192" # 2 vCPU, 8GB RAM
}

variable "database_name" {
  description = "Name of the application database"
  type        = string
  default     = "goingmerry_stonks"
}

variable "database_user" {
  description = "Database username"
  type        = string
  default     = "app_user"
}

variable "database_disk_size_gb" {
  description = "Initial disk size in GB"
  type        = number
  default     = 20
}

variable "database_max_disk_size_gb" {
  description = "Maximum disk size for autoresize in GB"
  type        = number
  default     = 100
}

variable "database_high_availability" {
  description = "Enable high availability (regional instance with failover)"
  type        = bool
  default     = true
}

variable "database_enable_pitr" {
  description = "Enable point-in-time recovery"
  type        = bool
  default     = true
}

variable "database_max_connections" {
  description = "Maximum number of concurrent database connections"
  type        = string
  default     = "100"
}

variable "database_authorized_networks" {
  description = "List of authorized networks for public database access"
  type = list(object({
    name = string
    cidr = string
  }))
  default = []
  # Example: [{ name = "office", cidr = "203.0.113.0/24" }]
}

# ========================================
# Networking Configuration
# ========================================

variable "enable_private_ip" {
  description = "Enable private IP for Cloud SQL (recommended for production)"
  type        = bool
  default     = true
}

variable "api_domain" {
  description = "Custom domain for the backend API (e.g., api.goingmerry-stonks.com)"
  type        = string
  default     = ""
}

variable "enable_ssl" {
  description = "Enable SSL certificate and HTTPS for API"
  type        = bool
  default     = true
}

variable "enable_cloud_armor" {
  description = "Enable Cloud Armor for DDoS protection and WAF"
  type        = bool
  default     = true
}

variable "rate_limit_requests" {
  description = "Maximum API requests per minute per IP address"
  type        = number
  default     = 100
}

variable "blocked_countries" {
  description = "List of country codes to block via Cloud Armor (ISO 3166-1 alpha-2)"
  type        = list(string)
  default     = []
  # Example: ["CN", "RU", "KP"]
}

variable "log_sample_rate" {
  description = "Sample rate for load balancer access logs (0.0 to 1.0)"
  type        = number
  default     = 1.0
}

# ========================================
# Monitoring Configuration
# ========================================

variable "enable_monitoring" {
  description = "Enable monitoring alerts"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for receiving monitoring alerts"
  type        = string
  default     = ""
}
