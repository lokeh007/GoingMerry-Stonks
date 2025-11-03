# Backend Module Outputs

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_v2_service.backend.name
}

output "service_url" {
  description = "URL of the backend Cloud Run service"
  value       = google_cloud_run_v2_service.backend.uri
}

output "service_account_email" {
  description = "Email of the backend service account"
  value       = google_service_account.backend.email
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository name for backend images"
  value       = google_artifact_registry_repository.backend.name
}

output "artifact_registry_url" {
  description = "Full URL for pushing Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}"
}

output "service_id" {
  description = "Full resource ID of the Cloud Run service"
  value       = google_cloud_run_v2_service.backend.id
}
