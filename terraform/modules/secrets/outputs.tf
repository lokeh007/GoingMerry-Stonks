# Secrets Module Outputs

output "polygon_api_key_secret_id" {
  description = "The ID of the Polygon API key secret (for IAM binding)"
  value       = google_secret_manager_secret.polygon_api_key.id
}

output "polygon_api_key_secret_name" {
  description = "The full resource name of the Polygon API key secret"
  value       = google_secret_manager_secret.polygon_api_key.name
}

output "polygon_api_key_version" {
  description = "The version name of the Polygon API key secret"
  value       = var.polygon_api_key != "" ? google_secret_manager_secret_version.polygon_api_key_version[0].name : null
}

output "database_url_secret_name" {
  description = "The full resource name of the database URL secret"
  value       = var.create_database_secret ? google_secret_manager_secret.database_url[0].name : null
}
