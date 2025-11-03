# Database Module Outputs

output "instance_name" {
  description = "Name of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.name
}

output "instance_connection_name" {
  description = "Connection name for Cloud SQL Proxy"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_name" {
  description = "Name of the application database"
  value       = google_sql_database.app_database.name
}

output "database_user" {
  description = "Database username"
  value       = google_sql_user.app_user.name
}

output "private_ip_address" {
  description = "Private IP address of the database instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "public_ip_address" {
  description = "Public IP address of the database instance"
  value       = google_sql_database_instance.postgres.public_ip_address
}

output "database_url_secret_name" {
  description = "Secret Manager secret name containing database URL"
  value       = google_secret_manager_secret.database_url.name
  sensitive   = true
}

output "database_url_secret_id" {
  description = "Secret Manager secret ID for database URL (for IAM binding)"
  value       = google_secret_manager_secret.database_url.id
}

output "db_password_secret_name" {
  description = "Secret Manager secret name containing database password"
  value       = google_secret_manager_secret.db_password.name
  sensitive   = true
}

output "db_password_secret_id" {
  description = "Secret Manager secret ID for database password (for IAM binding)"
  value       = google_secret_manager_secret.db_password.id
}

output "proxy_connection_string" {
  description = "Unix socket path for Cloud SQL Proxy"
  value       = local.proxy_connection_string
}

output "database_url" {
  description = "Full database connection URL (sensitive)"
  value       = local.database_url
  sensitive   = true
}
