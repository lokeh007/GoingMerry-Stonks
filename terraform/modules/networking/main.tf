# Networking Module - Load Balancer, SSL, Cloud Armor
# Simplified for Backend API only (Frontend uses Firebase Hosting)

# Reserve a global static IP address for the backend API
resource "google_compute_global_address" "backend_ip" {
  name         = "${var.environment}-backend-lb-ip"
  project      = var.project_id
  address_type = "EXTERNAL"
  ip_version   = "IPV4"

  labels = {
    environment = var.environment
    application = var.application_name
    tier        = "backend"
  }
}

# Google-managed SSL certificate for API domain
resource "google_compute_managed_ssl_certificate" "backend_ssl" {
  count   = var.enable_ssl && var.api_domain != "" ? 1 : 0
  name    = "${var.environment}-backend-ssl-cert"
  project = var.project_id

  managed {
    domains = [var.api_domain]
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Backend NEG for backend API Cloud Run
resource "google_compute_region_network_endpoint_group" "backend_neg" {
  name                  = "${var.environment}-backend-neg"
  project               = var.project_id
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = var.backend_service_name
  }
}

# Backend service for API
resource "google_compute_backend_service" "backend" {
  name                  = "${var.environment}-backend-service"
  project               = var.project_id
  protocol              = "HTTP"
  port_name             = "http"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  enable_cdn            = false # Don't cache API responses

  backend {
    group = google_compute_region_network_endpoint_group.backend_neg.id
  }

  # Cloud Armor security policy
  security_policy = var.enable_cloud_armor ? google_compute_security_policy.backend[0].id : null

  log_config {
    enable      = true
    sample_rate = var.log_sample_rate
  }

  # Note: Serverless NEGs (Cloud Run) don't use health checks or custom timeouts
  # Cloud Run has built-in health checking and request timeout management
}

# Backend bucket for frontend static files
resource "google_compute_backend_bucket" "frontend" {
  count       = var.frontend_bucket_name != "" ? 1 : 0
  name        = "${var.environment}-frontend-backend-bucket"
  project     = var.project_id
  bucket_name = var.frontend_bucket_name
  enable_cdn  = true

  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    client_ttl        = 3600
    default_ttl       = 3600
    max_ttl           = 86400
    negative_caching  = true
    serve_while_stale = 86400
  }
}

# URL map for API and Frontend
resource "google_compute_url_map" "backend" {
  name            = "${var.environment}-backend-url-map"
  project         = var.project_id
  default_service = var.frontend_bucket_name != "" ? google_compute_backend_bucket.frontend[0].id : google_compute_backend_service.backend.id

  # Route API requests to backend service
  host_rule {
    hosts        = ["*"]
    path_matcher = "allpaths"
  }

  path_matcher {
    name            = "allpaths"
    default_service = var.frontend_bucket_name != "" ? google_compute_backend_bucket.frontend[0].id : google_compute_backend_service.backend.id

    # API routes to backend service
    path_rule {
      paths   = ["/api/*", "/options/*", "/screener/*", "/health"]
      service = google_compute_backend_service.backend.id
    }

    # All other routes to frontend bucket (if configured)
    dynamic "path_rule" {
      for_each = var.frontend_bucket_name != "" ? [1] : []
      content {
        paths   = ["/*"]
        service = google_compute_backend_bucket.frontend[0].id
      }
    }
  }
}

# HTTP to HTTPS redirect
resource "google_compute_url_map" "https_redirect" {
  count   = var.enable_ssl ? 1 : 0
  name    = "${var.environment}-https-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

# HTTP target proxy (for redirect)
resource "google_compute_target_http_proxy" "redirect" {
  count   = var.enable_ssl ? 1 : 0
  name    = "${var.environment}-http-redirect-proxy"
  project = var.project_id
  url_map = google_compute_url_map.https_redirect[0].id
}

# HTTPS target proxy
resource "google_compute_target_https_proxy" "backend" {
  count   = var.enable_ssl ? 1 : 0
  name    = "${var.environment}-https-proxy"
  project = var.project_id
  url_map = google_compute_url_map.backend.id

  ssl_certificates = [
    google_compute_managed_ssl_certificate.backend_ssl[0].id
  ]

  ssl_policy = google_compute_ssl_policy.modern[0].id
}

# Target HTTP proxy (non-SSL fallback)
resource "google_compute_target_http_proxy" "backend_non_ssl" {
  count   = var.enable_ssl ? 0 : 1
  name    = "${var.environment}-http-proxy"
  project = var.project_id
  url_map = google_compute_url_map.backend.id
}

# Modern SSL policy
resource "google_compute_ssl_policy" "modern" {
  count           = var.enable_ssl ? 1 : 0
  name            = "${var.environment}-ssl-policy"
  project         = var.project_id
  profile         = "MODERN"
  min_tls_version = "TLS_1_2"
}

# Global forwarding rule for HTTPS
resource "google_compute_global_forwarding_rule" "https" {
  count                 = var.enable_ssl ? 1 : 0
  name                  = "${var.environment}-https-forwarding-rule"
  project               = var.project_id
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.backend[0].id
  ip_address            = google_compute_global_address.backend_ip.id

  labels = {
    environment = var.environment
    application = var.application_name
  }
}

# Global forwarding rule for HTTP (redirect to HTTPS)
resource "google_compute_global_forwarding_rule" "http" {
  name                  = "${var.environment}-http-forwarding-rule"
  project               = var.project_id
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = var.enable_ssl ? google_compute_target_http_proxy.redirect[0].id : google_compute_target_http_proxy.backend_non_ssl[0].id
  ip_address            = google_compute_global_address.backend_ip.id

  labels = {
    environment = var.environment
    application = var.application_name
  }
}

# Cloud Armor security policy for API
resource "google_compute_security_policy" "backend" {
  count   = var.enable_cloud_armor ? 1 : 0
  name    = "${var.environment}-backend-security-policy"
  project = var.project_id

  # Default rule - allow all
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rule"
  }

  # Rate limiting for API
  rule {
    action   = "rate_based_ban"
    priority = 1000
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"

      rate_limit_threshold {
        count        = var.rate_limit_requests
        interval_sec = 60
      }

      ban_duration_sec = 600
    }
    description = "API rate limiting - ${var.rate_limit_requests} req/min per IP"
  }

  # Block SQL injection attempts
  rule {
    action   = "deny(403)"
    priority = 2000
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-stable')"
      }
    }
    description = "Block SQL injection"
  }

  # Block XSS attempts
  rule {
    action   = "deny(403)"
    priority = 2001
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-stable')"
      }
    }
    description = "Block XSS attempts"
  }

  # Geo-blocking
  dynamic "rule" {
    for_each = length(var.blocked_countries) > 0 ? [1] : []
    content {
      action   = "deny(403)"
      priority = 3000
      match {
        expr {
          expression = join(" || ", [for c in var.blocked_countries : "origin.region_code == '${c}'"])
        }
      }
      description = "Geo-blocking"
    }
  }

  # DDoS protection
  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
    }
  }
}

# CORS configuration note:
# CORS is handled in the FastAPI application (app/main.py)
# Firebase Hosting will serve frontend and proxy /api/* to backend
