# Production Environment Outputs
# Architecture: Cloud Run (Backend) + Firebase Hosting (Frontend) + Cloud SQL (Database)

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
# Database Outputs
# ========================================

output "database_instance_name" {
  description = "Name of the Cloud SQL PostgreSQL instance"
  value       = module.database.instance_name
}

output "database_connection_name" {
  description = "Connection name for Cloud SQL Proxy"
  value       = module.database.instance_connection_name
}

output "database_private_ip" {
  description = "Private IP address of the database"
  value       = module.database.private_ip_address
}

output "database_url_secret" {
  description = "Secret Manager secret name containing database URL"
  value       = module.database.database_url_secret_name
  sensitive   = true
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

output "vpc_connector_id" {
  description = "VPC connector ID for Cloud Run to Cloud SQL"
  value       = var.enable_private_ip ? google_vpc_access_connector.connector[0].id : null
}

# ========================================
# Deployment Instructions
# ========================================

output "deployment_instructions" {
  description = "Next steps for deployment"
  value = <<-EOT

  ========================================
  DEPLOYMENT SUCCESSFUL - GoingMerry-Stonks Production
  ========================================

  Project ID: ${var.project_id}
  Region:     ${var.region}

  BACKEND API:
  -----------
  Cloud Run Service: ${module.backend.service_name}
  Direct URL:        ${module.backend.service_url}
  Load Balancer IP:  ${module.networking.backend_load_balancer_ip}
  API URL:           ${module.networking.api_url}
  ${var.api_domain != "" ? "Custom Domain:    ${var.api_domain} (configure DNS A record)" : ""}

  DATABASE:
  ---------
  Instance:          ${module.database.instance_name}
  Database Name:     ${var.database_name}
  Connection Name:   ${module.database.instance_connection_name}
  Private IP:        ${module.database.private_ip_address}

  FRONTEND:
  ---------
  Firebase Project:  ${var.project_id}
  Hosting URL:       https://${var.project_id}.web.app

  ========================================
  NEXT STEPS:
  ========================================

  1. Build and Push Backend Docker Image:
     -------------------------
     cd backend
     gcloud auth configure-docker ${var.region}-docker.pkg.dev
     docker build -t ${module.backend.artifact_registry_url}/api:v1.0.0 .
     docker push ${module.backend.artifact_registry_url}/api:v1.0.0

     # Update Cloud Run
     gcloud run services update ${module.backend.service_name} \
       --image=${module.backend.artifact_registry_url}/api:v1.0.0 \
       --region=${var.region}

  2. Deploy Frontend to Firebase Hosting:
     -------------------------
     cd frontend
     npm install
     npm run build

     # Install Firebase CLI if not already installed
     npm install -g firebase-tools

     # Login and deploy
     firebase login
     firebase deploy --only hosting

  3. Configure DNS for API (if using custom domain):
     -------------------------
     ${var.api_domain != "" ? "Add an A record:\n     Host: ${var.api_domain}\n     Type: A\n     Value: ${module.networking.backend_load_balancer_ip}\n     TTL: 300\n\n     Wait 15-20 minutes for SSL certificate to provision." : "Set api_domain variable and re-run terraform apply"}

  4. Configure Firebase Custom Domain (optional):
     -------------------------
     firebase hosting:channel:deploy CHANNEL_NAME
     # Follow instructions at: https://console.firebase.google.com/project/${var.project_id}/hosting/sites

  5. Test the Application:
     -------------------------
     # Test API health
     curl ${module.networking.api_url}/health

     # Test frontend
     open https://${var.project_id}.web.app

  6. Database Connection from Backend:
     -------------------------
     The backend connects to database via Cloud SQL Proxy over private IP.
     Connection string is stored in Secret Manager.

     To access database directly (for migrations):
     cloud_sql_proxy -instances=${module.database.instance_connection_name}=tcp:5432

  7. Monitor Services:
     -------------------------
     Cloud Run:    https://console.cloud.google.com/run?project=${var.project_id}
     Cloud SQL:    https://console.cloud.google.com/sql/instances?project=${var.project_id}
     Firebase:     https://console.firebase.google.com/project/${var.project_id}
     Logs:         https://console.cloud.google.com/logs?project=${var.project_id}
     Monitoring:   https://console.cloud.google.com/monitoring?project=${var.project_id}

  ========================================
  IMPORTANT SECURITY NOTES:
  ========================================

  1. Database credentials are stored in Secret Manager
  2. Backend uses Cloud SQL Proxy for secure database access
  3. API is protected by Cloud Armor (if enabled)
  4. SSL certificates auto-renew
  5. Regular backups are enabled (30-day retention)
  6. Point-in-time recovery is enabled (7-day window)

  ========================================
  EOT
}
