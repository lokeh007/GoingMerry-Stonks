# Secret Manager Module
# Manages application secrets using Google Cloud Secret Manager

resource "google_secret_manager_secret" "polygon_api_key" {
  secret_id = "${var.environment}-polygon-api-key"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    application = var.application_name
    managed_by  = "terraform"
  }
}

resource "google_secret_manager_secret_version" "polygon_api_key_version" {
  count = var.polygon_api_key != "" ? 1 : 0

  secret      = google_secret_manager_secret.polygon_api_key.id
  secret_data = var.polygon_api_key
}

# Optional: Additional secrets for future use
resource "google_secret_manager_secret" "database_url" {
  count     = var.create_database_secret ? 1 : 0
  secret_id = "${var.environment}-database-url"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    application = var.application_name
    managed_by  = "terraform"
  }
}
