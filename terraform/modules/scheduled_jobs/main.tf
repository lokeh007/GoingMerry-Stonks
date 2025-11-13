# Terraform Module: Scheduled Jobs
#
# Creates 3 Cloud Run Jobs and Cloud Schedulers to run daily stock screeners
# in batches after market close, with staggered execution times:
# - Batch 1: 4:30 PM ET (stocks A-H, ~2000 tickers)
# - Batch 2: 5:30 PM ET (stocks I-P, ~2000 tickers)
# - Batch 3: 6:30 PM ET (stocks Q-Z, ~2000 tickers)

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
  description = "Docker image for daily screeners"
  type        = string
  default     = "us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest"
}

# ============================================================================
# LOCALS - Batch Configuration
# ============================================================================

locals {
  # Define batch configurations
  # Staggered 90 minutes apart to prevent API rate limit conflicts
  batches = {
    batch-1 = {
      number      = 1
      description = "Daily stock screeners - Batch 1 (A-H, ~2000 stocks)"
      schedule    = "30 21 * * 1-5"  # 4:30 PM ET = 21:30 UTC
      time_label  = "4:30 PM ET"
    }
    batch-2 = {
      number      = 2
      description = "Daily stock screeners - Batch 2 (I-P, ~2000 stocks)"
      schedule    = "0 23 * * 1-5"   # 6:00 PM ET = 23:00 UTC (90 min after batch-1)
      time_label  = "6:00 PM ET"
    }
    batch-3 = {
      number      = 3
      description = "Daily stock screeners - Batch 3 (Q-Z, ~2000 stocks)"
      schedule    = "30 0 * * 2-6"   # 7:30 PM ET = 00:30 UTC next day (90 min after batch-2)
      time_label  = "7:30 PM ET"
    }
  }
}

# ============================================================================
# CLOUD RUN JOBS - Daily Screeners (3 Batches)
# ============================================================================

resource "google_cloud_run_v2_job" "daily_screeners_batch" {
  for_each = local.batches

  name     = "${var.environment}-daily-screeners-${each.key}"
  location = var.region
  project  = var.project_id

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    job_type    = "daily-screeners"
    batch       = each.key
  }

  template {
    labels = {
      environment = var.environment
      job_type    = "daily-screeners"
      batch       = each.key
    }

    template {
      timeout         = "${var.job_timeout}s"
      max_retries     = 1
      service_account = var.service_account_email

      containers {
        image = var.docker_image

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
# CLOUD SCHEDULER - Trigger Daily Jobs (3 Schedules)
# ============================================================================

resource "google_cloud_scheduler_job" "trigger_daily_screeners_batch" {
  for_each = local.batches

  name             = "${var.environment}-trigger-daily-screeners-${each.key}"
  description      = "${each.value.description} at ${each.value.time_label} Mon-Fri"
  schedule         = each.value.schedule
  time_zone        = "America/New_York"
  attempt_deadline = "1800s"  # Max allowed: 30 minutes (time for API call to complete, not job execution)
  project          = var.project_id
  region           = var.scheduler_region  # Use scheduler-specific region (us-east1)

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.daily_screeners_batch[each.key].name}:run"

    oauth_token {
      service_account_email = var.service_account_email
    }
  }

  depends_on = [
    google_cloud_run_v2_job.daily_screeners_batch
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

# Grant Cloud Scheduler permission to invoke the jobs
resource "google_cloud_run_v2_job_iam_member" "scheduler_invoker" {
  for_each = local.batches

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.daily_screeners_batch[each.key].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account_email}"
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "job_names" {
  description = "Cloud Run Job names for all batches"
  value = {
    for key, job in google_cloud_run_v2_job.daily_screeners_batch :
    key => job.name
  }
}

output "job_ids" {
  description = "Cloud Run Job IDs for all batches"
  value = {
    for key, job in google_cloud_run_v2_job.daily_screeners_batch :
    key => job.id
  }
}

output "scheduler_names" {
  description = "Cloud Scheduler job names for all batches"
  value = {
    for key, scheduler in google_cloud_scheduler_job.trigger_daily_screeners_batch :
    key => scheduler.name
  }
}

output "scheduler_schedules" {
  description = "Cron schedules for all batches"
  value = {
    for key, batch in local.batches :
    key => "${batch.schedule} (${batch.time_label})"
  }
}

output "batch_info" {
  description = "Complete batch configuration information"
  value = {
    for key, batch in local.batches :
    key => {
      batch_number = batch.number
      schedule     = batch.schedule
      time         = batch.time_label
      job_name     = google_cloud_run_v2_job.daily_screeners_batch[key].name
      scheduler    = google_cloud_scheduler_job.trigger_daily_screeners_batch[key].name
    }
  }
}
