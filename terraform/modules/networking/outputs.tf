# Networking Module Outputs

output "backend_load_balancer_ip" {
  description = "External IP address of the backend API load balancer"
  value       = google_compute_global_address.backend_ip.address
}

output "backend_ip_name" {
  description = "Name of the reserved IP address"
  value       = google_compute_global_address.backend_ip.name
}

output "ssl_certificate_id" {
  description = "ID of the managed SSL certificate"
  value       = var.enable_ssl && var.api_domain != "" ? google_compute_managed_ssl_certificate.backend_ssl[0].id : null
}

output "backend_service_id" {
  description = "ID of the backend service"
  value       = google_compute_backend_service.backend.id
}

output "security_policy_id" {
  description = "ID of the Cloud Armor security policy"
  value       = var.enable_cloud_armor ? google_compute_security_policy.backend[0].id : null
}

output "api_url" {
  description = "URL for the backend API"
  value       = var.enable_ssl && var.api_domain != "" ? "https://${var.api_domain}" : "http://${google_compute_global_address.backend_ip.address}"
}
