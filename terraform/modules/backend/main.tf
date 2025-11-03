# Backend API Module - Cloud Run
# Deploys FastAPI backend application to Cloud Run with auto-scaling

# Service account for backend Cloud Run service
resource "google_service_account" "backend" {
  account_id   = "${var.environment}-backend-sa"
  display_name = "Backend API Service Account - ${var.environment}"
  project      = var.project_id
  description  = "Service account for GoingMerry-Stonks backend API"
}

# Grant service account ability to write logs
resource "google_project_iam_member" "backend_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Grant service account ability to write metrics
resource "google_project_iam_member" "backend_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "backend" {
  location      = var.region
  repository_id = "${var.environment}-backend"
  description   = "Docker repository for backend API images"
  format        = "DOCKER"
  project       = var.project_id

  labels = {
    environment = var.environment
    application = var.application_name
    tier        = "backend"
  }
}

# Cloud Run service for backend API
resource "google_cloud_run_v2_service" "backend" {
  name     = "${var.environment}-backend-api"
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.backend.email

    # Scaling configuration
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    # Timeout for requests (max 3600s for Cloud Run)
    timeout = "300s"

    containers {
      image = var.backend_image

      # Resource limits
      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
        cpu_idle = true
        startup_cpu_boost = true
      }

      # Environment variables
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "API_HOST"
        value = "0.0.0.0"
      }

      env {
        name  = "API_PORT"
        value = "8000"
      }

      # Secret environment variable from Secret Manager
      env {
        name = "POLYGON_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.polygon_api_key_secret_name
            version = "latest"
          }
        }
      }

      # Health check on startup
      startup_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      # Liveness probe
      liveness_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 30
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3
      }

      ports {
        container_port = 8000
        name          = "http1"
      }
    }

    # VPC connector for private resources (if needed)
    dynamic "vpc_access" {
      for_each = var.vpc_connector_name != "" ? [1] : []
      content {
        connector = var.vpc_connector_name
        egress    = "PRIVATE_RANGES_ONLY"
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = {
    environment = var.environment
    application = var.application_name
    tier        = "backend"
    managed_by  = "terraform"
  }

  depends_on = [
    google_project_iam_member.backend_log_writer,
    google_project_iam_member.backend_metric_writer
  ]
}

# IAM policy to allow public access (adjust for production if needed)
resource "google_cloud_run_v2_service_iam_member" "backend_public_access" {
  count = var.allow_public_access ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# IAM policy for load balancer to invoke service (when using load balancer)
resource "google_cloud_run_v2_service_iam_member" "backend_lb_access" {
  count = var.load_balancer_service_account != "" ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.load_balancer_service_account}"
}
