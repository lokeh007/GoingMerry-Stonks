# Variables for Cloud Batch Jobs Module

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Batch jobs"
  type        = string
  default     = "us-east5"
}

variable "scheduler_region" {
  description = "GCP region for Cloud Scheduler (must be a supported region)"
  type        = string
  default     = "us-east1"
}

variable "environment" {
  description = "Environment name (prod, staging, dev)"
  type        = string
}

variable "service_account_email" {
  description = "Service account email for Cloud Batch jobs"
  type        = string
}

variable "polygon_api_key_secret" {
  description = "Secret Manager resource ID for Polygon API key"
  type        = string
}

variable "docker_image" {
  description = "Docker image for regular screeners"
  type        = string
  default     = "us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest"
}

variable "job_timeout_seconds" {
  description = "Job execution timeout in seconds (3 hours default)"
  type        = number
  default     = 10800

  validation {
    condition     = var.job_timeout_seconds >= 3600 && var.job_timeout_seconds <= 43200
    error_message = "Timeout must be between 1 hour (3600s) and 12 hours (43200s)."
  }
}

variable "vm_machine_type" {
  description = "Machine type for Spot VMs (e2-medium = 2 vCPU, 4GB)"
  type        = string
  default     = "e2-medium"

  validation {
    condition = contains([
      "e2-micro",       # 0.25-2 vCPU, 1GB
      "e2-small",       # 0.5-2 vCPU, 2GB
      "e2-medium",      # 1-2 vCPU, 4GB (recommended)
      "e2-standard-2",  # 2 vCPU, 8GB
      "e2-standard-4",  # 4 vCPU, 16GB
      "n2-standard-2",  # 2 vCPU, 8GB (newer generation)
      "n2-standard-4",  # 4 vCPU, 16GB
    ], var.vm_machine_type)
    error_message = "Machine type must be a valid e2 or n2 series VM."
  }
}

variable "rate_limit_per_minute" {
  description = "API requests per minute for screeners"
  type        = number
  default     = 58

  validation {
    condition     = var.rate_limit_per_minute > 0 && var.rate_limit_per_minute <= 100
    error_message = "Rate limit must be between 1 and 100 requests per minute."
  }
}

variable "vpc_network" {
  description = "VPC network for Cloud Batch (leave empty to use default)"
  type        = string
  default     = ""
}

variable "vpc_subnetwork" {
  description = "VPC subnetwork for Cloud Batch (leave empty to use default)"
  type        = string
  default     = ""
}

variable "enable_batches" {
  description = "Map of batches to enable (for phased rollout)"
  type        = map(bool)
  default = {
    batch-1 = true
    batch-2 = true
    batch-3 = true
    batch-4 = true
    batch-5 = true
  }
}
