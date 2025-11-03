# GoingMerry-Stonks Infrastructure Overview

Complete production-ready infrastructure for deploying a fintech platform to GCP.

## Architecture Summary

**Stack:** Cloud Run + Firebase Hosting + Cloud SQL PostgreSQL
**Project:** `sylvan-earth-477020-u6`
**Region:** `us-east5`

### Components

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Firebase Hosting | React SPA served via global CDN |
| **Backend API** | Cloud Run | FastAPI serverless containers |
| **Database** | Cloud SQL PostgreSQL 15 | Managed relational database with HA |
| **Load Balancer** | Cloud Load Balancing | SSL termination, routing |
| **Security** | Cloud Armor | WAF, DDoS protection, rate limiting |
| **Secrets** | Secret Manager | Encrypted credentials |
| **Networking** | VPC + Serverless Connector | Private database access |

## File Structure

```
GoingMerry-Stonks/
├── backend/
│   ├── Dockerfile                  # Production backend container
│   ├── .dockerignore
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── routers/                # API endpoints
│   │   ├── services/               # Business logic
│   │   └── models/                 # Pydantic models
│   └── requirements.txt            # Python dependencies
│
├── frontend/
│   ├── Dockerfile                  # nginx container (optional)
│   ├── nginx.conf                  # nginx config
│   ├── .env.production             # React build-time env vars
│   ├── src/                        # React application
│   └── package.json                # Node dependencies
│
├── terraform/
│   ├── backend.tf                  # Remote state in GCS
│   ├── README.md                   # Terraform documentation
│   ├── DEPLOYMENT.md               # Step-by-step deployment guide
│   │
│   ├── environments/
│   │   └── prod/
│   │       ├── main.tf             # Main orchestration
│   │       ├── variables.tf        # Input variables
│   │       ├── outputs.tf          # Output values
│   │       └── terraform.tfvars    # Secret values (gitignored)
│   │
│   └── modules/
│       ├── backend/                # Cloud Run backend module
│       ├── database/               # Cloud SQL PostgreSQL module
│       ├── networking/             # Load Balancer + Cloud Armor
│       └── secrets/                # Secret Manager module
│
├── firebase.json                   # Firebase Hosting config
├── .firebaserc                     # Firebase project config
├── cloudbuild.yaml                 # Cloud Build CI/CD
├── .github/
│   └── workflows/
│       └── deploy.yml              # GitHub Actions CI/CD
│
└── INFRASTRUCTURE.md               # This file
```

## Quick Deployment

### Prerequisites

```bash
# Install tools
brew install terraform gcloud
npm install -g firebase-tools

# Authenticate
gcloud auth login
gcloud config set project sylvan-earth-477020-u6
gcloud auth application-default login
```

### 1. Deploy Infrastructure

```bash
cd terraform/environments/prod

# Create terraform.tfvars from example
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Add your Polygon API key

# Create state bucket (one-time)
gcloud storage buckets create gs://goingmerry-stonks-terraform-state-prod \
  --location=us-east5 --uniform-bucket-level-access

# Deploy
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 2. Deploy Backend

```bash
# Get registry URL
BACKEND_REPO=$(cd terraform/environments/prod && terraform output -raw backend_artifact_registry_url)

# Build and push
cd backend
gcloud auth configure-docker us-east5-docker.pkg.dev
docker build -t ${BACKEND_REPO}/api:v1.0.0 .
docker push ${BACKEND_REPO}/api:v1.0.0

# Deploy to Cloud Run
gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.0.0 \
  --region=us-east5
```

### 3. Deploy Frontend

```bash
cd frontend
npm install
npm run build

# Deploy to Firebase Hosting
firebase login
firebase deploy --only hosting
```

### 4. Verify Deployment

```bash
# Test API
curl https://sylvan-earth-477020-u6.web.app/api/health

# Test frontend
open https://sylvan-earth-477020-u6.web.app
```

## Infrastructure Modules

### 1. Backend Module (`terraform/modules/backend/`)

**Creates:**
- Cloud Run service for FastAPI backend
- Service account with minimal permissions
- Artifact Registry repository for Docker images
- IAM bindings for Secret Manager access
- Auto-scaling configuration (1-10 instances)

**Key Features:**
- Cloud SQL Proxy sidecar for database access
- Secret Manager integration for credentials
- Health checks on `/health` endpoint
- Startup and liveness probes
- VPC connector for private networking

### 2. Database Module (`terraform/modules/database/`)

**Creates:**
- Cloud SQL PostgreSQL 15 instance
- Application database and user
- Automated backups (30-day retention)
- Point-in-time recovery (7-day window)
- High availability with automatic failover
- VPC peering for private IP
- Database credentials in Secret Manager

**Key Features:**
- Regional instance with failover replica
- Automated backups at 3 AM UTC
- Connection pooling support
- Query insights enabled
- Auto disk resize (20GB → 100GB max)

### 3. Networking Module (`terraform/modules/networking/`)

**Creates:**
- Global load balancer for backend API
- SSL certificate (auto-renewing)
- Cloud Armor security policy
- HTTP → HTTPS redirect
- Backend NEG for Cloud Run
- Health checks

**Key Features:**
- TLS 1.2+ only
- DDoS protection
- Rate limiting (100 req/min per IP)
- SQL injection & XSS protection
- Optional geo-blocking
- Adaptive protection against Layer 7 attacks

### 4. Secrets Module (`terraform/modules/secrets/`)

**Creates:**
- Secret for Polygon.io API key
- Secret for database password
- Secret for database URL
- IAM bindings for backend service account

**Key Features:**
- Automatic replication
- Version management
- Access audit logging

## Security Features

### Authentication & Authorization

- ✅ **Service Accounts** - Minimal permissions per service
- ✅ **Workload Identity** - No service account keys
- ✅ **IAM Bindings** - Explicit, least-privilege access
- ✅ **Secret Manager** - Encrypted credential storage

### Network Security

- ✅ **Private IP** - Database isolated in VPC
- ✅ **VPC Connector** - Secure Cloud Run → Cloud SQL
- ✅ **TLS Everywhere** - End-to-end encryption
- ✅ **Cloud Armor** - WAF + DDoS protection
- ✅ **Rate Limiting** - Per-IP throttling

### Data Protection

- ✅ **Automated Backups** - Daily at 3 AM UTC
- ✅ **PITR** - 7-day point-in-time recovery
- ✅ **Encryption at Rest** - Google-managed keys
- ✅ **Encryption in Transit** - TLS 1.2+
- ✅ **Deletion Protection** - Prevent accidental loss

### Compliance

- ✅ **Audit Logs** - All API calls logged
- ✅ **Access Logs** - Load balancer logs
- ✅ **Security Scanning** - Container vulnerability scanning
- ✅ **SSL/TLS** - A+ grade configuration

## Monitoring & Alerting

### Automatic Alerts

Configured in `terraform/environments/prod/main.tf`:

1. **High Error Rate** - > 5% 5xx responses for 5 minutes
2. **High Latency** - P95 > 2 seconds for 5 minutes
3. **Database Connections** - > 80% of max connections

### Dashboards

- **Cloud Run**: Request count, latency, instance count
- **Cloud SQL**: Connections, queries, storage
- **Load Balancer**: Traffic, SSL errors, backend health
- **Firebase**: Hosting bandwidth, errors

### Logs

```bash
# Backend logs
gcloud run services logs read prod-backend-api --region=us-east5

# Database logs
gcloud sql operations list --instance=prod-postgres-XXXX

# Load balancer logs
gcloud logging read "resource.type=http_load_balancer"

# Firebase logs
firebase hosting:channel:list
```

## Cost Breakdown

| Resource | Configuration | Monthly Cost |
|----------|--------------|-------------|
| **Cloud Run (Backend)** | 1-10 instances, 2 vCPU, 1GB RAM | $15-40 |
| **Cloud SQL PostgreSQL** | db-custom-2-8192, HA, 20GB | $150-200 |
| **Firebase Hosting** | Standard tier, global CDN | $0-5 |
| **Load Balancer** | Global LB + forwarding rules | $18 |
| **Cloud Armor** | Security policy + rules | $10-20 |
| **VPC Connector** | Serverless VPC access | $8 |
| **Artifact Registry** | Docker image storage | $1-5 |
| **Secret Manager** | 3 secrets | $0.30 |
| **Monitoring & Logging** | Standard tier | $5-15 |
| **Total** | | **~$210-320/month** |

### Cost Optimization Tips

1. **Scale to zero**: Set `backend_min_instances = 0` for dev
2. **Smaller database**: Use `db-custom-1-4096` for non-prod
3. **Disable HA**: Set `database_high_availability = false` for dev
4. **Reduce logs**: Set `log_sample_rate = 0.1` (10%)
5. **Use committed use discounts**: 57% discount for 3-year commit

## CI/CD Options

### Option 1: Cloud Build (Recommended)

Configured in `cloudbuild.yaml`:

```bash
# Create trigger
gcloud builds triggers create github \
  --repo-name=GoingMerry-Stonks \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

**Features:**
- Builds on push to `main`
- Parallel backend + frontend builds
- Automatic deployment
- Smoke tests

### Option 2: GitHub Actions

Configured in `.github/workflows/deploy.yml`:

**Setup:**
1. Configure Workload Identity Federation
2. Add secrets to GitHub repo
3. Push to `main` to deploy

## Disaster Recovery

### Backup Strategy

- **Database Backups**: Daily at 3 AM UTC, 30-day retention
- **Point-in-Time Recovery**: Up to 7 days
- **Terraform State**: Versioned in GCS
- **Docker Images**: Tagged and retained in Artifact Registry

### Recovery Procedures

#### Database Restore

```bash
# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --backup-instance=prod-postgres-XXXX \
  --backup-project=sylvan-earth-477020-u6

# Point-in-time recovery
gcloud sql instances clone prod-postgres-XXXX NEW_INSTANCE \
  --point-in-time='2024-01-15T10:30:00Z'
```

#### Rollback Deployment

```bash
# Rollback backend
gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.0.0 \
  --region=us-east5

# Rollback frontend
firebase hosting:clone SOURCE_SITE_ID:SOURCE_CHANNEL TARGET_SITE_ID:live
```

#### Restore Terraform State

```bash
# List state versions
gcloud storage ls -l gs://goingmerry-stonks-terraform-state-prod/terraform/state/

# Restore specific version
gcloud storage cp gs://goingmerry-stonks-terraform-state-prod/terraform/state/default.tfstate#VERSION \
  ./terraform.tfstate.backup
```

## Maintenance

### Regular Tasks

**Weekly:**
- Review monitoring dashboards
- Check cost reports
- Review security alerts

**Monthly:**
- Review and rotate secrets
- Update dependencies
- Review access logs

**Quarterly:**
- Update Terraform modules
- Review and update security policies
- Conduct disaster recovery drill

### Updates

```bash
# Update backend
docker build -t ${BACKEND_REPO}/api:v1.1.0 backend/
docker push ${BACKEND_REPO}/api:v1.1.0
gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.1.0 \
  --region=us-east5

# Update infrastructure
cd terraform/environments/prod
terraform plan -out=tfplan
terraform apply tfplan
```

## Support & Documentation

- **Terraform Docs**: `terraform/README.md`
- **Deployment Guide**: `terraform/DEPLOYMENT.md`
- **Backend API**: `backend/README.md` + `CLAUDE.md`
- **Frontend**: `frontend/README.md`

### Useful Links

- [GCP Console](https://console.cloud.google.com/home/dashboard?project=sylvan-earth-477020-u6)
- [Cloud Run](https://console.cloud.google.com/run?project=sylvan-earth-477020-u6)
- [Cloud SQL](https://console.cloud.google.com/sql/instances?project=sylvan-earth-477020-u6)
- [Firebase Console](https://console.firebase.google.com/project/sylvan-earth-477020-u6)
- [Cloud Armor](https://console.cloud.google.com/net-security/securitypolicies?project=sylvan-earth-477020-u6)

## Contributing

When making infrastructure changes:

1. Create a feature branch
2. Update relevant module
3. Run `terraform fmt` and `terraform validate`
4. Create a plan: `terraform plan -out=tfplan`
5. Review plan carefully
6. Test in a dev environment first
7. Apply to production: `terraform apply tfplan`
8. Document changes in commit message

## License

MIT License - See LICENSE file
