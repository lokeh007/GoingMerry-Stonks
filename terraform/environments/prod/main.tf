# Production Environment Configuration
# Architecture: Cloud Run (Backend) + Firebase Hosting (Frontend) + Firestore (Database)

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

# Configure providers
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",              # Cloud Run
    "compute.googleapis.com",          # Compute Engine (for LB)
    "artifactregistry.googleapis.com", # Artifact Registry
    "secretmanager.googleapis.com",    # Secret Manager
    "cloudbuild.googleapis.com",       # Cloud Build
    "firebase.googleapis.com",         # Firebase
    "firebasehosting.googleapis.com",  # Firebase Hosting
    "firestore.googleapis.com",        # Cloud Firestore
    "cloudscheduler.googleapis.com",   # Cloud Scheduler
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Data source for project
data "google_project" "project" {
  project_id = var.project_id
}

# Backend module
module "backend" {
  source = "../../modules/backend"

  project_id       = var.project_id
  region           = var.region
  environment      = var.environment
  application_name = var.application_name

  backend_image               = var.backend_image
  polygon_api_key_secret_name = module.secrets.polygon_api_key_secret_name

  min_instances = var.backend_min_instances
  max_instances = var.backend_max_instances
  cpu_limit     = var.backend_cpu_limit
  memory_limit  = var.backend_memory_limit

  # Use load balancer for ingress
  allow_public_access           = false
  load_balancer_service_account = ""

  # No VPC connector needed
  vpc_connector_name = ""

  depends_on = [
    google_project_service.required_apis,
    module.secrets
  ]
}

# Secrets module
module "secrets" {
  source = "../../modules/secrets"

  project_id       = var.project_id
  environment      = var.environment
  application_name = var.application_name
  polygon_api_key  = var.polygon_api_key

  depends_on = [google_project_service.required_apis]
}

# Grant backend service account access to Polygon API key secret
resource "google_secret_manager_secret_iam_member" "backend_polygon_access" {
  secret_id = module.secrets.polygon_api_key_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.backend.service_account_email}"

  depends_on = [module.secrets, module.backend]
}

# Firestore Database
resource "google_firestore_database" "main" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  # Enable delete protection in production
  delete_protection_state = var.environment == "prod" ? "DELETE_PROTECTION_ENABLED" : "DELETE_PROTECTION_DISABLED"

  depends_on = [google_project_service.required_apis]
}

# Grant backend service account Firestore access
resource "google_project_iam_member" "backend_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${module.backend.service_account_email}"
}

# Networking module (Load Balancer for Backend API and Frontend)
module "networking" {
  source = "../../modules/networking"

  project_id       = var.project_id
  region           = var.region
  environment      = var.environment
  application_name = var.application_name

  backend_service_name = module.backend.service_name
  frontend_bucket_name = "sylvan-earth-477020-u6-frontend"

  api_domain          = var.api_domain
  enable_ssl          = var.enable_ssl
  enable_cloud_armor  = var.enable_cloud_armor
  rate_limit_requests = var.rate_limit_requests
  blocked_countries   = var.blocked_countries
  log_sample_rate     = var.log_sample_rate

  depends_on = [
    google_project_service.required_apis,
    module.backend
  ]
}

# Scheduled Jobs module (Daily Screeners)
module "scheduled_jobs" {
  source = "../../modules/scheduled_jobs"

  project_id       = var.project_id
  region           = var.region
  environment      = var.environment

  polygon_api_key_secret = module.secrets.polygon_api_key_secret_id
  service_account_email  = module.backend.service_account_email

  # Docker images for screener jobs (use versioned tags from terraform.tfvars)
  docker_image             = var.docker_image
  smart_money_docker_image = var.smart_money_docker_image

  # Schedule: 6:30 PM ET Monday-Friday (after market close)
  job_schedule = "30 23 * * 1-5"  # 23:30 UTC = 6:30 PM ET

  # Resource allocation for processing ~6000 stocks
  job_timeout = 10800  # 3 hours (increased for Quick Win - will reduce with parallel processing)
  job_memory  = "512Mi"  # TESTING: Reduced from 2Gi for cost optimization
  job_cpu     = "1"      # TESTING: Reduced from 2 to match memory reduction

  depends_on = [
    google_project_service.required_apis,
    module.backend,
    module.secrets,
    google_firestore_database.main
  ]
}

# Monitoring and Alerting
resource "google_monitoring_notification_channel" "email" {
  count        = var.alert_email != "" ? 1 : 0
  display_name = "Email Notifications - ${var.environment}"
  type         = "email"
  project      = var.project_id

  labels = {
    email_address = var.alert_email
  }
}

# Alert: High error rate
resource "google_monitoring_alert_policy" "high_error_rate" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${var.environment} - High Error Rate"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Error rate > 5%"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.alert_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "86400s"
  }
}

# Alert: High latency
resource "google_monitoring_alert_policy" "high_latency" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${var.environment} - High Latency"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Latency > 2 seconds"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 2000

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
        group_by_fields      = ["resource.service_name"]
      }
    }
  }

  notification_channels = var.alert_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "86400s"
  }
}

