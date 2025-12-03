# Terraform Module: Scheduled Jobs
#
# DISABLED: All nightly screener jobs have been disabled.
# The Cloud Run Jobs and Cloud Schedulers below are commented out
# to allow Terraform to delete these resources.
#
# Previously created:
# - 5 jobs for Regular Screeners (Undiscovered + Coiled Spring)
# - 5 jobs for Smart Money Screener (Options Flow)
# - 10 Cloud Schedulers to trigger the jobs
#
# To re-enable, uncomment the resources below.

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# ============================================================================
# VARIABLES
# ============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run Job"
  type        = string
  default     = "us-east5"
}

variable "scheduler_region" {
  description = "GCP region for Cloud Scheduler (must be a supported region)"
  type        = string
  default     = "us-east1"  # Closest supported region to us-east5
}

variable "environment" {
  description = "Environment name (prod, staging, dev)"
  type        = string
}

variable "polygon_api_key_secret" {
  description = "Secret Manager resource ID for Polygon API key"
  type        = string
}

variable "service_account_email" {
  description = "Service account email for Cloud Run Job"
  type        = string
}

variable "job_schedule" {
  description = "DEPRECATED - Ignored in favor of batch schedules"
  type        = string
  default     = "30 23 * * 1-5"  # Kept for backward compatibility
}

variable "job_timeout" {
  description = "Job execution timeout in seconds (per batch)"
  type        = number
  default     = 10800  # 3 hours (actual runtime ~95 minutes, with buffer for occasional delays)
}

variable "job_memory" {
  description = "Memory allocation for job"
  type        = string
  default     = "512Mi"  # Default optimized for typical screener workloads
}

variable "job_cpu" {
  description = "CPU allocation for job"
  type        = string
  default     = "1"
}

variable "docker_image" {
  description = "Docker image for regular screeners (Undiscovered + Coiled Spring)"
  type        = string
  default     = "us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest"
}

variable "smart_money_docker_image" {
  description = "Docker image for Smart Money screener (Options Flow) - Uses same backend image since job is included"
  type        = string
  default     = "us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:latest"
}

variable "regular_screeners_rate_limit" {
  description = "API requests per minute for regular screeners (Undiscovered + Coiled Spring)"
  type        = number
  default     = 50  # Lowered from 60 to provide headroom for retry overhead

  validation {
    condition     = var.regular_screeners_rate_limit > 0 && var.regular_screeners_rate_limit <= 100
    error_message = "Regular screeners rate limit must be between 1 and 100 requests per minute."
  }
}

variable "smart_money_rate_limit" {
  description = "API requests per minute for Smart Money screeners (Options Flow) - lower due to ~3 API calls per ticker (2 option expiries + 1 fundamentals)"
  type        = number
  default     = 36  # Accounts for 3 API calls per ticker (36 req/min ÷ 3 = 12 tickers/min, ~100 min per 1200-stock batch)

  validation {
    condition     = var.smart_money_rate_limit > 0 && var.smart_money_rate_limit <= 100
    error_message = "Smart Money rate limit must be between 1 and 100 requests per minute."
  }
}

# ============================================================================
# LOCALS - Batch Configuration (kept for reference when re-enabling)
# ============================================================================

# locals {
#   # Define batch configurations for Regular Screeners
#   regular_batches = {
#     batch-1 = { number = 1, description = "Regular stock screeners - Batch 1 (A-D)", schedule = "30 16 * * 1-5", time_label = "4:30 PM ET" }
#     batch-2 = { number = 2, description = "Regular stock screeners - Batch 2 (E-J)", schedule = "0 18 * * 1-5", time_label = "6:00 PM ET" }
#     batch-3 = { number = 3, description = "Regular stock screeners - Batch 3 (K-N)", schedule = "30 19 * * 1-5", time_label = "7:30 PM ET" }
#     batch-4 = { number = 4, description = "Regular stock screeners - Batch 4 (O-S)", schedule = "0 21 * * 1-5", time_label = "9:00 PM ET" }
#     batch-5 = { number = 5, description = "Regular stock screeners - Batch 5 (T-Z)", schedule = "30 22 * * 1-5", time_label = "10:30 PM ET" }
#   }
#
#   # Define batch configurations for Smart Money Screener
#   smart_money_batches = {
#     batch-1 = { number = 1, description = "Smart Money screener - Batch 1 (A-D)", schedule = "15 0 * * 2-6", time_label = "12:15 AM ET" }
#     batch-2 = { number = 2, description = "Smart Money screener - Batch 2 (E-J)", schedule = "30 2 * * 2-6", time_label = "2:30 AM ET" }
#     batch-3 = { number = 3, description = "Smart Money screener - Batch 3 (K-N)", schedule = "0 5 * * 2-6", time_label = "5:00 AM ET" }
#     batch-4 = { number = 4, description = "Smart Money screener - Batch 4 (O-S)", schedule = "30 7 * * 2-6", time_label = "7:30 AM ET" }
#     batch-5 = { number = 5, description = "Smart Money screener - Batch 5 (T-Z)", schedule = "0 10 * * 2-6", time_label = "10:00 AM ET" }
#   }
# }

# ============================================================================
# CLOUD RUN JOBS - DISABLED
# All screener jobs commented out for deletion via terraform apply
# ============================================================================

# DISABLED: Regular Screeners Cloud Run Jobs
# resource "google_cloud_run_v2_job" "regular_screeners_batch" { ... }

# DISABLED: Smart Money Screeners Cloud Run Jobs  
# resource "google_cloud_run_v2_job" "smart_money_screeners_batch" { ... }

# ============================================================================
# CLOUD SCHEDULER - DISABLED
# All schedulers commented out for deletion via terraform apply
# ============================================================================

# DISABLED: Regular Screeners Cloud Schedulers
# resource "google_cloud_scheduler_job" "trigger_regular_screeners_batch" { ... }

# DISABLED: Smart Money Screeners Cloud Schedulers
# resource "google_cloud_scheduler_job" "trigger_smart_money_screeners_batch" { ... }

# ============================================================================
# IAM - Firestore Access for Jobs
# ============================================================================

# Grant Cloud Run Job access to Firestore (kept for other potential uses)
resource "google_project_iam_member" "job_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${var.service_account_email}"
}

# DISABLED: IAM for screener jobs
# resource "google_cloud_run_v2_job_iam_member" "regular_scheduler_invoker" { ... }
# resource "google_cloud_run_v2_job_iam_member" "smart_money_scheduler_invoker" { ... }

# ============================================================================
# OUTPUTS - All outputs removed since resources are disabled
# ============================================================================

# No outputs - all screener job resources have been disabled
