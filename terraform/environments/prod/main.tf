# Production Environment Configuration
# Architecture: Cloud Run (Backend) + Firebase Hosting (Frontend) + Cloud SQL (Database)

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
    "sqladmin.googleapis.com",         # Cloud SQL
    "servicenetworking.googleapis.com", # VPC Peering for Cloud SQL
    "firebase.googleapis.com",         # Firebase
    "firebasehosting.googleapis.com",  # Firebase Hosting
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

# VPC Network for Cloud SQL private IP (optional but recommended)
resource "google_compute_network" "vpc" {
  count                   = var.enable_private_ip ? 1 : 0
  name                    = "${var.environment}-vpc"
  project                 = var.project_id
  auto_create_subnetworks = true

  depends_on = [google_project_service.required_apis]
}

# VPC Peering for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  count         = var.enable_private_ip ? 1 : 0
  name          = "${var.environment}-private-ip"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc[0].id

  depends_on = [google_project_service.required_apis]
}

resource "google_service_networking_connection" "private_vpc_connection" {
  count                   = var.enable_private_ip ? 1 : 0
  network                 = google_compute_network.vpc[0].id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address[0].name]

  depends_on = [google_project_service.required_apis]
}

# Serverless VPC connector for Cloud Run to access Cloud SQL
resource "google_vpc_access_connector" "connector" {
  count         = var.enable_private_ip ? 1 : 0
  name          = "${var.environment}-vpc-connector"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.vpc[0].name
  ip_cidr_range = "10.8.0.0/28"

  depends_on = [google_project_service.required_apis]
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

  # VPC connector for Cloud SQL access
  vpc_connector_name = var.enable_private_ip ? google_vpc_access_connector.connector[0].id : ""

  depends_on = [
    google_project_service.required_apis,
    module.secrets,
    module.database
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

# Database module
module "database" {
  source = "../../modules/database"

  project_id       = var.project_id
  region           = var.region
  environment      = var.environment
  application_name = var.application_name

  database_version = var.database_version
  database_tier    = var.database_tier
  database_name    = var.database_name
  database_user    = var.database_user

  disk_size_gb                 = var.database_disk_size_gb
  max_disk_size_gb             = var.database_max_disk_size_gb
  high_availability            = var.database_high_availability
  enable_point_in_time_recovery = var.database_enable_pitr
  max_connections              = var.database_max_connections

  vpc_network_id                = var.enable_private_ip ? google_compute_network.vpc[0].id : ""
  authorized_networks           = var.database_authorized_networks

  depends_on = [
    google_project_service.required_apis,
    google_service_networking_connection.private_vpc_connection
  ]
}

# Grant backend service account access to database secrets
resource "google_secret_manager_secret_iam_member" "backend_db_password_access" {
  secret_id = module.database.db_password_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.backend.service_account_email}"

  depends_on = [module.database, module.backend]
}

resource "google_secret_manager_secret_iam_member" "backend_db_url_access" {
  secret_id = module.database.database_url_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.backend.service_account_email}"

  depends_on = [module.database, module.backend]
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

# Alert: Database high connections
resource "google_monitoring_alert_policy" "db_high_connections" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${var.environment} - Database High Connections"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Active connections > 80%"

    condition_threshold {
      filter          = "resource.type = \"cloudsql_database\" AND metric.type = \"cloudsql.googleapis.com/database/postgresql/num_backends\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = tonumber(var.database_max_connections) * 0.8

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.alert_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "86400s"
  }
}
