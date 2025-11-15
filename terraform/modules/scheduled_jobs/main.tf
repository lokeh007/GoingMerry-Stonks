# Terraform Module: Scheduled Jobs
#
# Creates 10 Cloud Run Jobs and Cloud Schedulers:
# - 5 jobs for Regular Screeners (Undiscovered + Coiled Spring)
# - 5 jobs for Smart Money Screener (Options Flow)
#
# Regular Screeners (60 req/min):
# - Batch 1: 4:30 PM ET (A-D, ~1200 stocks) → finishes 6:00 PM
# - Batch 2: 6:00 PM ET (E-J, ~1200 stocks) → finishes 7:30 PM
# - Batch 3: 7:30 PM ET (K-N, ~1200 stocks) → finishes 9:00 PM
# - Batch 4: 9:00 PM ET (O-S, ~1200 stocks) → finishes 10:30 PM
# - Batch 5: 10:30 PM ET (T-Z, ~1200 stocks) → finishes 12:00 AM
#
# Smart Money Screeners (45 req/min):
# - Batch 1: 12:15 AM ET (A-D, ~1200 stocks) → finishes 2:15 AM [15-min buffer]
# - Batch 2: 2:00 AM ET (E-J, ~1200 stocks) → finishes 4:00 AM
# - Batch 3: 4:00 AM ET (K-N, ~1200 stocks) → finishes 6:00 AM
# - Batch 4: 6:00 AM ET (O-S, ~1200 stocks) → finishes 8:00 AM
# - Batch 5: 8:00 AM ET (T-Z, ~1200 stocks) → finishes 10:00 AM

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
  default     = 10800  # 3 hours (increased from 2 hours for Quick Win)
}

variable "job_memory" {
  description = "Memory allocation for job"
  type        = string
  default     = "2Gi"
}

variable "job_cpu" {
  description = "CPU allocation for job"
  type        = string
  default     = "2"
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
  default     = 60

  validation {
    condition     = var.regular_screeners_rate_limit > 0 && var.regular_screeners_rate_limit <= 100
    error_message = "Regular screeners rate limit must be between 1 and 100 requests per minute."
  }
}

variable "smart_money_rate_limit" {
  description = "API requests per minute for Smart Money screeners (Options Flow) - lower due to higher token consumption"
  type        = number
  default     = 45

  validation {
    condition     = var.smart_money_rate_limit > 0 && var.smart_money_rate_limit <= 100
    error_message = "Smart Money rate limit must be between 1 and 100 requests per minute."
  }
}

# ============================================================================
# LOCALS - Batch Configuration
# ============================================================================

locals {
  # Define batch configurations for Regular Screeners
  # Staggered 90 minutes apart to prevent API rate limit conflicts
  # Runs: Undiscovered + Coiled Spring (60 req/min)
  regular_batches = {
    batch-1 = {
      number      = 1
      description = "Regular stock screeners - Batch 1 (A-D, ~1200 stocks)"
      schedule    = "30 16 * * 1-5"  # 4:30 PM ET Mon-Fri
      time_label  = "4:30 PM ET"
    }
    batch-2 = {
      number      = 2
      description = "Regular stock screeners - Batch 2 (E-J, ~1200 stocks)"
      schedule    = "0 18 * * 1-5"   # 6:00 PM ET Mon-Fri
      time_label  = "6:00 PM ET"
    }
    batch-3 = {
      number      = 3
      description = "Regular stock screeners - Batch 3 (K-N, ~1200 stocks)"
      schedule    = "30 19 * * 1-5"  # 7:30 PM ET Mon-Fri
      time_label  = "7:30 PM ET"
    }
    batch-4 = {
      number      = 4
      description = "Regular stock screeners - Batch 4 (O-S, ~1200 stocks)"
      schedule    = "0 21 * * 1-5"   # 9:00 PM ET Mon-Fri
      time_label  = "9:00 PM ET"
    }
    batch-5 = {
      number      = 5
      description = "Regular stock screeners - Batch 5 (T-Z, ~1200 stocks)"
      schedule    = "30 22 * * 1-5"  # 10:30 PM ET Mon-Fri
      time_label  = "10:30 PM ET"
    }
  }

  # Define batch configurations for Smart Money Screener
  # Staggered 2 hours apart, runs AFTER regular screeners complete
  # Runs: Smart Money Options Flow only (45 req/min)
  # NOTE: Batch 1 starts at 12:15 AM (15-min buffer) to prevent overlap with regular batch 5
  smart_money_batches = {
    batch-1 = {
      number      = 1
      description = "Smart Money screener - Batch 1 (A-D, ~1200 stocks)"
      schedule    = "15 0 * * 2-6"   # 12:15 AM ET Tue-Sat (15-min buffer after regular batch 5)
      time_label  = "12:15 AM ET"
    }
    batch-2 = {
      number      = 2
      description = "Smart Money screener - Batch 2 (E-J, ~1200 stocks)"
      schedule    = "0 2 * * 2-6"    # 2:00 AM ET Tue-Sat
      time_label  = "2:00 AM ET"
    }
    batch-3 = {
      number      = 3
      description = "Smart Money screener - Batch 3 (K-N, ~1200 stocks)"
      schedule    = "0 4 * * 2-6"    # 4:00 AM ET Tue-Sat
      time_label  = "4:00 AM ET"
    }
    batch-4 = {
      number      = 4
      description = "Smart Money screener - Batch 4 (O-S, ~1200 stocks)"
      schedule    = "0 6 * * 2-6"    # 6:00 AM ET Tue-Sat
      time_label  = "6:00 AM ET"
    }
    batch-5 = {
      number      = 5
      description = "Smart Money screener - Batch 5 (T-Z, ~1200 stocks)"
      schedule    = "0 8 * * 2-6"    # 8:00 AM ET Tue-Sat
      time_label  = "8:00 AM ET"
    }
  }
}

# ============================================================================
# CLOUD RUN JOBS - Regular Screeners (5 Batches)
# Undiscovered + Coiled Spring @ 60 req/min
# ============================================================================

resource "google_cloud_run_v2_job" "regular_screeners_batch" {
  for_each = local.regular_batches

  name     = "${var.environment}-regular-screeners-${each.key}"
  location = var.region
  project  = var.project_id

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    job_type    = "regular-screeners"
    batch       = each.key
  }

  template {
    labels = {
      environment = var.environment
      job_type    = "regular-screeners"
      batch       = each.key
    }

    template {
      timeout         = "${var.job_timeout}s"
      max_retries     = 0  # Disabled - Let application-level retry logic (exponential backoff with jitter) handle failures
      service_account = var.service_account_email

      containers {
        image = var.docker_image

        # Command to run daily screeners job
        command = ["python"]
        args    = ["/app/jobs/run_daily_screeners.py"]

        resources {
          limits = {
            cpu    = var.job_cpu
            memory = var.job_memory
          }
        }

        # Environment variables
        env {
          name  = "BATCH_NUMBER"
          value = tostring(each.value.number)
        }

        env {
          name = "POLYGON_API_KEY"
          value_source {
            secret_key_ref {
              secret  = var.polygon_api_key_secret
              version = "latest"
            }
          }
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        }

        env {
          name  = "RATE_LIMIT_PER_MINUTE"
          value = tostring(var.regular_screeners_rate_limit)
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
    ]
  }
}

# ============================================================================
# CLOUD RUN JOBS - Smart Money Screener (5 Batches)
# Options Flow @ 45 req/min
# ============================================================================

resource "google_cloud_run_v2_job" "smart_money_screeners_batch" {
  for_each = local.smart_money_batches

  name     = "${var.environment}-smart-money-screeners-${each.key}"
  location = var.region
  project  = var.project_id

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    job_type    = "smart-money-screeners"
    batch       = each.key
  }

  template {
    labels = {
      environment = var.environment
      job_type    = "smart-money-screeners"
      batch       = each.key
    }

    template {
      timeout         = "${var.job_timeout}s"
      max_retries     = 0  # Disabled - Let application-level retry logic (exponential backoff with jitter) handle failures
      service_account = var.service_account_email

      containers {
        image = var.smart_money_docker_image

        # Command to run smart money screener job
        command = ["python"]
        args    = ["/app/jobs/run_smart_money_screener.py"]

        resources {
          limits = {
            cpu    = var.job_cpu
            memory = var.job_memory
          }
        }

        # Environment variables
        env {
          name  = "BATCH_NUMBER"
          value = tostring(each.value.number)
        }

        env {
          name = "POLYGON_API_KEY"
          value_source {
            secret_key_ref {
              secret  = var.polygon_api_key_secret
              version = "latest"
            }
          }
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        }

        env {
          name  = "RATE_LIMIT_PER_MINUTE"
          value = tostring(var.smart_money_rate_limit)
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
    ]
  }
}

# ============================================================================
# CLOUD SCHEDULER - Trigger Regular Screeners (5 Schedules)
# ============================================================================

resource "google_cloud_scheduler_job" "trigger_regular_screeners_batch" {
  for_each = local.regular_batches

  name             = "${var.environment}-trigger-regular-screeners-${each.key}"
  description      = "${each.value.description} at ${each.value.time_label} Mon-Fri"
  schedule         = each.value.schedule
  time_zone        = "America/New_York"
  attempt_deadline = "1800s"  # Max allowed: 30 minutes (time for API call to complete, not job execution)
  project          = var.project_id
  region           = var.scheduler_region  # Use scheduler-specific region (us-east1)

  retry_config {
    retry_count = 0  # Disabled - Let application-level retry logic (exponential backoff with jitter) handle failures
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.regular_screeners_batch[each.key].name}:run"

    oauth_token {
      service_account_email = var.service_account_email
    }
  }

  depends_on = [
    google_cloud_run_v2_job.regular_screeners_batch
  ]
}

# ============================================================================
# CLOUD SCHEDULER - Trigger Smart Money Screeners (5 Schedules)
# ============================================================================

resource "google_cloud_scheduler_job" "trigger_smart_money_screeners_batch" {
  for_each = local.smart_money_batches

  name             = "${var.environment}-trigger-smart-money-screeners-${each.key}"
  description      = "${each.value.description} at ${each.value.time_label} Tue-Sat"
  schedule         = each.value.schedule
  time_zone        = "America/New_York"
  attempt_deadline = "1800s"  # Max allowed: 30 minutes (time for API call to complete, not job execution)
  project          = var.project_id
  region           = var.scheduler_region  # Use scheduler-specific region (us-east1)

  retry_config {
    retry_count = 0  # Disabled - Let application-level retry logic (exponential backoff with jitter) handle failures
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.smart_money_screeners_batch[each.key].name}:run"

    oauth_token {
      service_account_email = var.service_account_email
    }
  }

  depends_on = [
    google_cloud_run_v2_job.smart_money_screeners_batch
  ]
}

# ============================================================================
# IAM - Firestore Access for Jobs
# ============================================================================

# Grant Cloud Run Job access to Firestore
resource "google_project_iam_member" "job_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${var.service_account_email}"
}

# Grant Cloud Scheduler permission to invoke regular screener jobs
resource "google_cloud_run_v2_job_iam_member" "regular_scheduler_invoker" {
  for_each = local.regular_batches

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.regular_screeners_batch[each.key].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account_email}"
}

# Grant Cloud Scheduler permission to invoke Smart Money screener jobs
resource "google_cloud_run_v2_job_iam_member" "smart_money_scheduler_invoker" {
  for_each = local.smart_money_batches

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.smart_money_screeners_batch[each.key].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account_email}"
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "regular_job_names" {
  description = "Cloud Run Job names for regular screeners (all batches)"
  value = {
    for key, job in google_cloud_run_v2_job.regular_screeners_batch :
    key => job.name
  }
}

output "smart_money_job_names" {
  description = "Cloud Run Job names for Smart Money screeners (all batches)"
  value = {
    for key, job in google_cloud_run_v2_job.smart_money_screeners_batch :
    key => job.name
  }
}

output "regular_job_ids" {
  description = "Cloud Run Job IDs for regular screeners (all batches) - for monitoring and automation"
  value = {
    for key, job in google_cloud_run_v2_job.regular_screeners_batch :
    key => job.id
  }
}

output "smart_money_job_ids" {
  description = "Cloud Run Job IDs for Smart Money screeners (all batches) - for monitoring and automation"
  value = {
    for key, job in google_cloud_run_v2_job.smart_money_screeners_batch :
    key => job.id
  }
}

output "all_job_ids" {
  description = "Combined map of all Cloud Run Job IDs (regular + smart money) - for backwards compatibility"
  value = merge(
    { for key, job in google_cloud_run_v2_job.regular_screeners_batch : "regular-${key}" => job.id },
    { for key, job in google_cloud_run_v2_job.smart_money_screeners_batch : "smart-money-${key}" => job.id }
  )
}

output "regular_scheduler_names" {
  description = "Cloud Scheduler job names for regular screeners"
  value = {
    for key, scheduler in google_cloud_scheduler_job.trigger_regular_screeners_batch :
    key => scheduler.name
  }
}

output "smart_money_scheduler_names" {
  description = "Cloud Scheduler job names for Smart Money screeners"
  value = {
    for key, scheduler in google_cloud_scheduler_job.trigger_smart_money_screeners_batch :
    key => scheduler.name
  }
}

output "regular_batch_info" {
  description = "Complete regular screener batch configuration"
  value = {
    for key, batch in local.regular_batches :
    key => {
      batch_number = batch.number
      schedule     = batch.schedule
      time         = batch.time_label
      job_name     = google_cloud_run_v2_job.regular_screeners_batch[key].name
      scheduler    = google_cloud_scheduler_job.trigger_regular_screeners_batch[key].name
    }
  }
}

output "smart_money_batch_info" {
  description = "Complete Smart Money screener batch configuration"
  value = {
    for key, batch in local.smart_money_batches :
    key => {
      batch_number = batch.number
      schedule     = batch.schedule
      time         = batch.time_label
      job_name     = google_cloud_run_v2_job.smart_money_screeners_batch[key].name
      scheduler    = google_cloud_scheduler_job.trigger_smart_money_screeners_batch[key].name
    }
  }
}
