# GoingMerry-Stonks Terraform Infrastructure

Production-ready infrastructure for deploying GoingMerry-Stonks fintech platform to Google Cloud Platform.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRODUCTION                               │
│                    Project: sylvan-earth-477020-u6              │
│                    Region: us-east5                             │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│  Firebase        │         │   Cloud Load     │
│  Hosting         │         │   Balancer       │
│  (Frontend)      │         │  + Cloud Armor   │
│                  │         │  + SSL           │
└────────┬─────────┘         └────────┬─────────┘
         │                            │
         │                            │
         │ /api/*  ┌─────────────────┴─────────────────┐
         └────────►│                                    │
                   │      Cloud Run - Backend API       │
                   │      (FastAPI + Uvicorn)          │
                   │                                    │
                   └──────────┬───────────┬────────────┘
                              │           │
                              │           │ Cloud SQL Proxy
                              │           │ (Unix Socket)
                   ┌──────────▼───────┐   │
                   │  Secret Manager  │   │
                   │  - Polygon Key   │   │
                   │  - DB Password   │   │
                   │  - DB URL        │   │
                   └──────────────────┘   │
                                          │
                              ┌───────────▼────────────┐
                              │   Cloud SQL PostgreSQL │
                              │   (High Availability)  │
                              │   - Auto Backups       │
                              │   - PITR Enabled       │
                              │   - Private IP         │
                              └────────────────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Cloud Run | Serverless container platform for FastAPI |
| **Frontend** | Firebase Hosting | Global CDN for React SPA |
| **Database** | Cloud SQL PostgreSQL 15 | Managed relational database |
| **Load Balancer** | Cloud Load Balancing | HTTPS termination, routing |
| **Security** | Cloud Armor | WAF, DDoS protection, rate limiting |
| **Secrets** | Secret Manager | Encrypted credential storage |
| **Registry** | Artifact Registry | Docker image storage |
| **VPC** | VPC + Serverless Connector | Private database connectivity |

## Module Structure

```
terraform/
├── backend.tf                      # Remote state configuration
├── environments/
│   └── prod/
│       ├── main.tf                 # Main orchestration
│       ├── variables.tf            # Environment variables
│       ├── outputs.tf              # Output values
│       └── terraform.tfvars        # Secret values (DO NOT COMMIT)
└── modules/
    ├── backend/                    # Cloud Run backend
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── database/                   # Cloud SQL PostgreSQL
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── networking/                 # Load Balancer + Cloud Armor
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    └── secrets/                    # Secret Manager
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

## Prerequisites

1. **gcloud CLI** - [Install](https://cloud.google.com/sdk/docs/install)
2. **Terraform** >= 1.5.0 - [Install](https://developer.hashicorp.com/terraform/downloads)
3. **Firebase CLI** - `npm install -g firebase-tools`
4. **Docker** - For building images
5. **GCP Project** - `sylvan-earth-477020-u6`
6. **Polygon.io API Key** - [Get Key](https://polygon.io/)

## Quick Start

### 1. Initial Setup

```bash
# Authenticate
gcloud auth login
gcloud config set project sylvan-earth-477020-u6
gcloud auth application-default login

# Enable billing API
gcloud services enable cloudbilling.googleapis.com

# Create state bucket
gcloud storage buckets create gs://goingmerry-stonks-terraform-state-prod \
  --location=us-east5 \
  --uniform-bucket-level-access \
  --public-access-prevention

gcloud storage buckets update gs://goingmerry-stonks-terraform-state-prod \
  --versioning
```

### 2. Configure Variables

```bash
cd terraform/environments/prod
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Edit with your values
```

**Required values:**
- `polygon_api_key` - Your Polygon.io API key
- `backend_image` - Will be set after first build
- `alert_email` - Your email for alerts

### 3. Deploy Infrastructure

```bash
# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan
```

**This creates:**
- ✅ Cloud Run service for backend
- ✅ Cloud SQL PostgreSQL instance (high availability)
- ✅ Load Balancer with SSL
- ✅ Cloud Armor security policy
- ✅ Secret Manager secrets
- ✅ VPC and Serverless Connector
- ✅ Artifact Registry repositories
- ✅ Monitoring alerts

### 4. Build and Deploy

```bash
# Get registry URL from Terraform output
BACKEND_REPO=$(terraform output -raw backend_artifact_registry_url)

# Build and push backend
cd ../../../backend
gcloud auth configure-docker us-east5-docker.pkg.dev
docker build -t ${BACKEND_REPO}/api:v1.0.0 .
docker push ${BACKEND_REPO}/api:v1.0.0

# Update Cloud Run
gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.0.0 \
  --region=us-east5

# Build and deploy frontend
cd ../frontend
npm install
npm run build
firebase login
firebase deploy --only hosting
```

## Cost Estimation

| Resource | Monthly Cost (Production) |
|----------|-------------------------|
| Cloud Run Backend (1-10 instances) | $15-40 |
| Cloud SQL PostgreSQL (db-custom-2-8192, HA) | $150-200 |
| Firebase Hosting | $0-5 (free tier covers most) |
| Load Balancer | $18 (fixed) |
| Cloud Armor | $10-20 |
| VPC Connector | $8 |
| Artifact Registry | $1-5 |
| Secret Manager | $0.30 |
| **Total** | **~$200-300/month** |

## Security Features

- ✅ **Private Database Access** - Cloud SQL accessible only via VPC
- ✅ **Secret Management** - All credentials in Secret Manager
- ✅ **TLS Encryption** - End-to-end HTTPS with auto-renewing certs
- ✅ **DDoS Protection** - Cloud Armor with adaptive protection
- ✅ **Rate Limiting** - 100 req/min per IP (configurable)
- ✅ **WAF Rules** - SQL injection, XSS protection
- ✅ **Geo-blocking** - Optional country-level blocking
- ✅ **Deletion Protection** - Prevents accidental deletion
- ✅ **Automated Backups** - 30-day retention + PITR

## Operations

### View Logs

```bash
# Backend logs
gcloud run services logs read prod-backend-api --region=us-east5 --limit=50

# Database logs
gcloud sql operations list --instance=prod-postgres-XXXX

# Load balancer logs
gcloud logging read "resource.type=http_load_balancer" --limit=20
```

### Scale Services

```bash
# Update terraform.tfvars
backend_min_instances = 2
backend_max_instances = 20

# Apply changes
terraform apply
```

### Database Access

```bash
# Via Cloud SQL Proxy
cloud_sql_proxy -instances=INSTANCE_CONNECTION_NAME=tcp:5432

# Then connect with psql
psql "host=127.0.0.1 port=5432 dbname=goingmerry_stonks user=app_user"
```

### Rollback Deployment

```bash
# Rollback to previous image
gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.0.0 \
  --region=us-east5
```

## Monitoring

Access monitoring dashboards:

- **Cloud Run**: https://console.cloud.google.com/run?project=sylvan-earth-477020-u6
- **Cloud SQL**: https://console.cloud.google.com/sql/instances?project=sylvan-earth-477020-u6
- **Firebase**: https://console.firebase.google.com/project/sylvan-earth-477020-u6
- **Logs**: https://console.cloud.google.com/logs?project=sylvan-earth-477020-u6
- **Monitoring**: https://console.cloud.google.com/monitoring?project=sylvan-earth-477020-u6

## Troubleshooting

### Database Connection Issues

```bash
# Check VPC connector
gcloud compute networks vpc-access connectors describe prod-vpc-connector \
  --region=us-east5

# Test database connectivity
gcloud sql connect INSTANCE_NAME --user=postgres
```

### SSL Certificate Not Provisioning

```bash
# Check certificate status
gcloud compute ssl-certificates describe prod-backend-ssl-cert --global

# Verify DNS
dig api.your-domain.com +short
```

### High Costs

To reduce costs:
1. Set `backend_min_instances = 0` (scale to zero)
2. Disable `database_high_availability = false` (for non-prod)
3. Use smaller database tier: `db-custom-1-4096`
4. Reduce log sampling: `log_sample_rate = 0.1`

## Cleanup

**WARNING: This destroys all resources and data!**

```bash
cd terraform/environments/prod
terraform destroy
gcloud storage rm -r gs://goingmerry-stonks-terraform-state-prod
```

## Support

For detailed deployment instructions, see `DEPLOYMENT.md`.

For issues:
1. Check Terraform outputs
2. Review Cloud Run logs
3. Verify Secret Manager permissions
4. Check VPC connector status

## License

MIT License - See LICENSE file for details
