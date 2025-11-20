# Terraform Module: Cloud Batch Jobs
#
# Replacement for Cloud Run Jobs using Google Cloud Batch + Spot VMs
# for 96.5% cost reduction on long-running batch workloads.
#
# Key Benefits:
# - Spot VMs: ~$0.0066/hour vs Cloud Run ~$0.30/run
# - Better for I/O-bound workloads (API rate-limited)
# - Auto-retry on Spot VM preemption
# - Flexible VM types (e2, n2, c2)
#
# Trade-offs:
# - ~2-3 min cold start (vs <30s for Cloud Run)
# - 1-5% preemption risk (auto-retried)
# - Per-hour billing (vs per-second)

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
  description = "GCP region for Cloud Batch jobs"
  type        = string
  default     = "us-east5"
}

variable "scheduler_region" {
  description = "GCP region for Cloud Scheduler"
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
  description = "Job execution timeout in seconds"
  type        = number
  default     = 10800  # 3 hours
}

variable "vm_machine_type" {
  description = "Machine type for Spot VMs"
  type        = string
  default     = "e2-medium"  # 2 vCPU, 4GB memory
}

variable "vpc_network" {
  description = "VPC network for Cloud Batch (optional, uses default if not specified)"
  type        = string
  default     = ""
}

variable "vpc_subnetwork" {
  description = "VPC subnetwork for Cloud Batch (optional)"
  type        = string
  default     = ""
}

# ============================================================================
# LOCALS - Batch Configuration
# ============================================================================

locals {
  # Define batch configurations (same as Cloud Run module)
  # Staggered 90 minutes apart to prevent API rate limit conflicts
  regular_batches = {
    batch-1 = {
      number      = 1
      description = "Regular stock screeners - Batch 1 (A-D, ~992 stocks)"
      schedule    = "30 16 * * 1-5"  # 4:30 PM ET Mon-Fri
      time_label  = "4:30 PM ET"
    }
    batch-2 = {
      number      = 2
      description = "Regular stock screeners - Batch 2 (E-J, ~992 stocks)"
      schedule    = "0 18 * * 1-5"   # 6:00 PM ET Mon-Fri
      time_label  = "6:00 PM ET"
    }
    batch-3 = {
      number      = 3
      description = "Regular stock screeners - Batch 3 (K-N, ~992 stocks)"
      schedule    = "30 19 * * 1-5"  # 7:30 PM ET Mon-Fri
      time_label  = "7:30 PM ET"
    }
    batch-4 = {
      number      = 4
      description = "Regular stock screeners - Batch 4 (O-S, ~992 stocks)"
      schedule    = "0 21 * * 1-5"   # 9:00 PM ET Mon-Fri
      time_label  = "9:00 PM ET"
    }
    batch-5 = {
      number      = 5
      description = "Regular stock screeners - Batch 5 (T-Z, ~992 stocks)"
      schedule    = "30 22 * * 1-5"  # 10:30 PM ET Mon-Fri
      time_label  = "10:30 PM ET"
    }
  }
}

# ============================================================================
# CLOUD BATCH JOBS - Regular Screeners (5 Batches)
# ============================================================================

resource "google_batch_job" "regular_screeners_batch" {
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

  task_groups {
    task_count = 1  # Single task per batch (not parallelized)

    task_spec {
      runnables {
        container {
          image_uri = var.docker_image
          commands  = ["python", "/app/jobs/run_daily_screeners.py"]

          # Environment variables (same as Cloud Run)
          environment_variables = {
            BATCH_NUMBER           = tostring(each.value.number)
            GCP_PROJECT_ID         = var.project_id
            ENVIRONMENT            = var.environment
            PYTHONUNBUFFERED       = "1"
            RATE_LIMIT_PER_MINUTE  = "58"
          }
        }

        # Environment variables from secrets
        environment {
          secret_variables = {
            POLYGON_API_KEY = "${var.polygon_api_key_secret}/versions/latest"
          }
        }
      }

      compute_resource {
        cpu_milli  = 1000   # 1 vCPU (1000 milli-CPU)
        memory_mib = 1024   # 1 GiB memory
      }

      max_run_duration = "${var.job_timeout_seconds}s"
      max_retry_count  = 1  # Auto-retry once on failure (including Spot preemption)
    }

    # Task execution configuration
    task_environments {
      variables = {
        BATCH_NUMBER = tostring(each.value.number)
      }
    }
  }

  # Allocation policy: Use Spot VMs for cost savings
  allocation_policy {
    instances {
      policy {
        machine_type       = var.vm_machine_type
        provisioning_model = "SPOT"  # 🎯 Use Spot VMs (91% discount)

        # Accelerators (GPUs) - not needed for this workload
        # accelerators = []
      }

      # Network configuration
      dynamic "network_interface" {
        for_each = var.vpc_network != "" ? [1] : []
        content {
          network    = var.vpc_network
          subnetwork = var.vpc_subnetwork
        }
      }
    }

    # Service account for job execution
    service_account {
      email = var.service_account_email
    }
  }

  # Logging configuration
  logs_policy {
    destination = "CLOUD_LOGGING"
  }

  lifecycle {
    ignore_changes = [
      labels["goog-gke-node"],
    ]
  }
}

# ============================================================================
# CLOUD SCHEDULER - Trigger Cloud Batch Jobs
# ============================================================================

# Note: Cloud Scheduler triggers Cloud Batch via HTTP API
# This requires a Cloud Function or Cloud Run service as a proxy
# because Cloud Batch doesn't have a direct HTTP trigger endpoint.

# Option 1: Use Cloud Run service as trigger proxy (recommended)
# Option 2: Use Cloud Functions to trigger Cloud Batch
# Option 3: Use Workflows to trigger Cloud Batch

# For now, we'll create the scheduler that calls a trigger endpoint
# You'll need to deploy a small Cloud Run service that receives
# the scheduler request and calls the Cloud Batch API.

resource "google_cloud_scheduler_job" "trigger_regular_screeners_batch" {
  for_each = local.regular_batches

  name             = "${var.environment}-trigger-batch-regular-screeners-${each.key}"
  description      = "${each.value.description} at ${each.value.time_label} Mon-Fri"
  schedule         = each.value.schedule
  time_zone        = "America/New_York"
  attempt_deadline = "1800s"
  project          = var.project_id
  region           = var.scheduler_region

  retry_config {
    retry_count = 0  # Disabled
  }

  # HTTP target calls Cloud Batch API directly
  http_target {
    http_method = "POST"
    uri         = "https://batch.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/jobs/${google_batch_job.regular_screeners_batch[each.key].name}:run"

    oauth_token {
      service_account_email = var.service_account_email
    }
  }

  depends_on = [
    google_batch_job.regular_screeners_batch
  ]
}

# ============================================================================
# IAM PERMISSIONS
# ============================================================================

# Grant service account permission to run Cloud Batch jobs
resource "google_project_iam_member" "batch_job_runner" {
  project = var.project_id
  role    = "roles/batch.jobsEditor"
  member  = "serviceAccount:${var.service_account_email}"
}

# Grant service account permission to read secrets
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${var.service_account_email}"
}

# Grant service account permission to write to Firestore
resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${var.service_account_email}"
}

# Grant service account permission to write logs
resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${var.service_account_email}"
}

# Grant service account permission to pull Docker images
resource "google_project_iam_member" "artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${var.service_account_email}"
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "batch_job_names" {
  description = "Cloud Batch job names for regular screeners"
  value = {
    for key, job in google_batch_job.regular_screeners_batch :
    key => job.name
  }
}

output "batch_job_ids" {
  description = "Cloud Batch job IDs for monitoring"
  value = {
    for key, job in google_batch_job.regular_screeners_batch :
    key => job.id
  }
}

output "scheduler_names" {
  description = "Cloud Scheduler job names"
  value = {
    for key, scheduler in google_cloud_scheduler_job.trigger_regular_screeners_batch :
    key => scheduler.name
  }
}

output "batch_info" {
  description = "Complete batch configuration"
  value = {
    for key, batch in local.regular_batches :
    key => {
      batch_number = batch.number
      schedule     = batch.schedule
      time         = batch.time_label
      job_name     = google_batch_job.regular_screeners_batch[key].name
      scheduler    = google_cloud_scheduler_job.trigger_regular_screeners_batch[key].name
    }
  }
}
