# Production Environment Outputs
# Architecture: Cloud Run (Backend) + Firebase Hosting (Frontend) + Firestore (Database)

# ========================================
# Backend API Outputs
# ========================================

output "backend_service_url" {
  description = "Direct URL to backend Cloud Run service"
  value       = module.backend.service_url
}

output "backend_service_name" {
  description = "Name of backend Cloud Run service"
  value       = module.backend.service_name
}

output "backend_artifact_registry_url" {
  description = "Artifact Registry URL for pushing backend images"
  value       = module.backend.artifact_registry_url
}

output "api_load_balancer_ip" {
  description = "Public IP address of the API load balancer"
  value       = module.networking.backend_load_balancer_ip
}

output "api_url" {
  description = "URL to access the backend API"
  value       = module.networking.api_url
}

# ========================================
# Database Outputs (Firestore)
# ========================================

output "firestore_database_name" {
  description = "Name of the Firestore database"
  value       = google_firestore_database.main.name
}

output "firestore_location" {
  description = "Firestore database location"
  value       = google_firestore_database.main.location_id
}

# ========================================
# Frontend (Firebase Hosting)
# ========================================

output "firebase_hosting_url" {
  description = "Firebase Hosting URL for frontend"
  value       = "https://${var.project_id}.web.app"
}

output "firebase_project_id" {
  description = "Firebase project ID"
  value       = var.project_id
}

# ========================================
# Networking Outputs
# ========================================

output "load_balancer_ip" {
  description = "Load balancer IP address"
  value       = module.networking.backend_load_balancer_ip
}


# ========================================
# Deployment Instructions
# ========================================

output "deployment_instructions" {
  description = "Next steps for deployment"
  value = "See README.md for deployment instructions"
}
