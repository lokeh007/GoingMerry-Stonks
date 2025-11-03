# Cloud SQL PostgreSQL Database Module
# Production-ready PostgreSQL instance with high availability and backups

# Random suffix for database instance name (must be globally unique)
resource "random_id" "db_suffix" {
  byte_length = 4
}

# Cloud SQL PostgreSQL instance
resource "google_sql_database_instance" "postgres" {
  name             = "${var.environment}-postgres-${random_id.db_suffix.hex}"
  database_version = var.database_version
  region           = var.region
  project          = var.project_id

  # Prevent accidental deletion in production
  deletion_protection = var.environment == "prod" ? true : false

  settings {
    tier              = var.database_tier
    availability_type = var.high_availability ? "REGIONAL" : "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = var.disk_size_gb
    disk_autoresize   = true
    disk_autoresize_limit = var.max_disk_size_gb

    # Backup configuration
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00" # 3 AM UTC
      point_in_time_recovery_enabled = var.enable_point_in_time_recovery
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
        retention_unit   = "COUNT"
      }
    }

    # Maintenance window
    maintenance_window {
      day          = 7 # Sunday
      hour         = 4 # 4 AM UTC
      update_track = "stable"
    }

    # IP configuration
    ip_configuration {
      ipv4_enabled    = true
      private_network = var.vpc_network_id
      require_ssl     = true

      # Authorized networks for public access (if needed)
      dynamic "authorized_networks" {
        for_each = var.authorized_networks
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.cidr
        }
      }
    }

    # Database flags for performance and security
    database_flags {
      name  = "max_connections"
      value = var.max_connections
    }

    database_flags {
      name  = "shared_buffers"
      value = "262144" # 2GB for db-custom-4-16384
    }

    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }

    database_flags {
      name  = "log_lock_waits"
      value = "on"
    }

    # Enable query insights
    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
    }
  }
}

# Create application database
resource "google_sql_database" "app_database" {
  name     = var.database_name
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id

  charset   = "UTF8"
  collation = "en_US.UTF8"
}

# Generate random password for database user
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Create database user
resource "google_sql_user" "app_user" {
  name     = var.database_user
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
  password = random_password.db_password.result
}

# Store database password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.environment}-db-password"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    application = var.application_name
  }
}

resource "google_secret_manager_secret_version" "db_password_version" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Connection name for database URL
locals {
  connection_name = google_sql_database_instance.postgres.connection_name
  database_url    = "postgresql://${google_sql_user.app_user.name}:${random_password.db_password.result}@${google_sql_database_instance.postgres.private_ip_address}:5432/${google_sql_database.app_database.name}"

  # Cloud SQL Proxy connection string
  proxy_connection_string = "/cloudsql/${local.connection_name}"
}

# Store database URL in Secret Manager
resource "google_secret_manager_secret" "database_url" {
  secret_id = "${var.environment}-database-url"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    application = var.application_name
  }
}

resource "google_secret_manager_secret_version" "database_url_version" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.database_url
}
