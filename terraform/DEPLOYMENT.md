# GoingMerry-Stonks Infrastructure Deployment Guide

This guide provides step-by-step instructions for deploying the GoingMerry-Stonks platform to Google Cloud Platform using Terraform.

## Prerequisites

### Required Tools

1. **gcloud CLI** - [Install Guide](https://cloud.google.com/sdk/docs/install)
2. **Terraform** >= 1.5.0 - [Install Guide](https://developer.hashicorp.com/terraform/downloads)
3. **Docker** - For building images locally (optional)
4. **Git** - For version control

### GCP Project Setup

Your project details:
- **Project ID**: `sylvan-earth-477020-u6`
- **Region**: `us-east5`

## Initial Setup (One-Time)

### 1. Authenticate with GCP

```bash
# Login to Google Cloud
gcloud auth login

# Set the project
gcloud config set project sylvan-earth-477020-u6

# Authenticate for application default credentials
gcloud auth application-default login
```

### 2. Enable Required APIs

```bash
# The Terraform will enable most APIs, but enable billing API manually
gcloud services enable cloudbilling.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

### 3. Create Terraform State Bucket

```bash
# Create GCS bucket for Terraform state
gcloud storage buckets create gs://goingmerry-stonks-terraform-state-prod \
  --location=us-east5 \
  --uniform-bucket-level-access \
  --public-access-prevention

# Enable versioning for state backup
gcloud storage buckets update gs://goingmerry-stonks-terraform-state-prod \
  --versioning
```

### 4. Configure Terraform Variables

```bash
cd terraform/environments/prod

# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required Configuration in `terraform.tfvars`:**

```hcl
# Project Configuration
project_id = "sylvan-earth-477020-u6"
region     = "us-east5"

# Secrets (CRITICAL - NEVER COMMIT THIS FILE)
polygon_api_key = "YOUR_POLYGON_API_KEY_HERE"

# Docker Images (will be built and pushed)
backend_image  = "us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:v1.0.0"
frontend_image = "us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-frontend/web:v1.0.0"

# Domain (optional - leave empty to use load balancer IP)
custom_domain = "" # e.g., "app.goingmerry-stonks.com"

# Security
enable_ssl         = true
enable_cdn         = true
enable_cloud_armor = true
rate_limit_requests = 100

# Monitoring
enable_monitoring = true
alert_email       = "your-email@example.com"
```

## Deployment Steps

### Step 1: Initialize Terraform

```bash
cd terraform/environments/prod

# Initialize Terraform (downloads providers, configures backend)
terraform init

# Verify configuration
terraform validate
```

### Step 2: Plan Infrastructure Changes

```bash
# Preview what will be created
terraform plan -out=tfplan

# Review the plan carefully
# Expected resources: ~30-40 resources will be created
```

### Step 3: Apply Infrastructure

```bash
# Apply the infrastructure changes
terraform apply tfplan

# Or apply with auto-approval (use with caution)
# terraform apply -auto-approve

# This will take approximately 5-10 minutes
```

**Expected Output:**
```
Apply complete! Resources: 35 added, 0 changed, 0 destroyed.

Outputs:
application_url = "http://34.XXX.XXX.XXX"
backend_service_url = "https://prod-backend-api-XXXXX-ue.a.run.app"
frontend_service_url = "https://prod-frontend-XXXXX-ue.a.run.app"
load_balancer_ip = "34.XXX.XXX.XXX"
```

### Step 4: Build and Push Docker Images

After infrastructure is created, build and deploy your application:

```bash
# Get the artifact registry URLs from Terraform output
BACKEND_REPO=$(terraform output -raw backend_artifact_registry_url)
FRONTEND_REPO=$(terraform output -raw frontend_artifact_registry_url)

# Configure Docker authentication
gcloud auth configure-docker us-east5-docker.pkg.dev

# Build and push backend
cd ../../../backend
docker build -t ${BACKEND_REPO}/api:v1.0.0 -t ${BACKEND_REPO}/api:latest .
docker push ${BACKEND_REPO}/api:v1.0.0
docker push ${BACKEND_REPO}/api:latest

# Build and push frontend
cd ../frontend
docker build -t ${FRONTEND_REPO}/web:v1.0.0 -t ${FRONTEND_REPO}/web:latest .
docker push ${FRONTEND_REPO}/web:v1.0.0
docker push ${FRONTEND_REPO}/web:latest
```

### Step 5: Update Cloud Run Services with Images

```bash
# Update backend service
gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.0.0 \
  --region=us-east5

# Update frontend service
gcloud run services update prod-frontend \
  --image=${FRONTEND_REPO}/web:v1.0.0 \
  --region=us-east5
```

### Step 6: Configure DNS (Optional)

If using a custom domain:

```bash
# Get the load balancer IP
LB_IP=$(terraform output -raw load_balancer_ip)

# Add an A record in your DNS provider:
# Type: A
# Name: app (or @ for root domain)
# Value: <LB_IP>
# TTL: 300 (or default)

# Example for Cloud DNS:
gcloud dns record-sets create app.goingmerry-stonks.com. \
  --zone=your-zone-name \
  --type=A \
  --ttl=300 \
  --rrdatas=${LB_IP}
```

### Step 7: Wait for SSL Certificate (If Enabled)

If you configured a custom domain and enabled SSL:

```bash
# Check SSL certificate status
gcloud compute ssl-certificates describe prod-ssl-cert --global

# Wait until status shows "ACTIVE" (can take 15-20 minutes)
# The certificate provisions after DNS propagation
```

## Verification

### Check Service Health

```bash
# Get service URLs
BACKEND_URL=$(gcloud run services describe prod-backend-api --region=us-east5 --format='value(status.url)')
FRONTEND_URL=$(gcloud run services describe prod-frontend --region=us-east5 --format='value(status.url)')

# Test backend health
curl ${BACKEND_URL}/health

# Test frontend
curl ${FRONTEND_URL}

# Test through load balancer
LB_IP=$(terraform output -raw load_balancer_ip)
curl http://${LB_IP}/health
```

### View Logs

```bash
# Backend logs
gcloud run services logs read prod-backend-api --region=us-east5 --limit=50

# Frontend logs
gcloud run services logs read prod-frontend --region=us-east5 --limit=50

# Load balancer logs
gcloud logging read "resource.type=http_load_balancer" --limit=20 --format=json
```

### Access Cloud Console

- **Cloud Run**: https://console.cloud.google.com/run?project=sylvan-earth-477020-u6
- **Load Balancer**: https://console.cloud.google.com/net-services/loadbalancing?project=sylvan-earth-477020-u6
- **Logs**: https://console.cloud.google.com/logs?project=sylvan-earth-477020-u6
- **Monitoring**: https://console.cloud.google.com/monitoring?project=sylvan-earth-477020-u6

## CI/CD Setup (Optional)

### Option 1: Cloud Build Triggers

```bash
# Create a Cloud Build trigger for automatic deployments
gcloud builds triggers create github \
  --repo-name=GoingMerry-Stonks \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --region=us-east5
```

### Option 2: GitHub Actions

1. Set up Workload Identity Federation:
```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool"

# Create Workload Identity Provider
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository_owner=='YOUR_GITHUB_USERNAME'"
```

2. Create Service Account:
```bash
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:github-actions-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:github-actions-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

3. Add secrets to GitHub repository:
   - `GCP_WORKLOAD_IDENTITY_PROVIDER`
   - `GCP_SERVICE_ACCOUNT`

## Maintenance

### Update Application

```bash
# Build new version
docker build -t ${BACKEND_REPO}/api:v1.0.1 ./backend
docker push ${BACKEND_REPO}/api:v1.0.1

# Deploy
gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.0.1 \
  --region=us-east5
```

### Update Infrastructure

```bash
cd terraform/environments/prod

# Make changes to .tf files or variables
nano terraform.tfvars

# Plan and apply
terraform plan -out=tfplan
terraform apply tfplan
```

### Scale Services

```bash
# Update scaling in terraform.tfvars
backend_min_instances = 2
backend_max_instances = 20

# Apply changes
terraform apply -auto-approve
```

## Disaster Recovery

### Backup State

```bash
# Terraform state is automatically versioned in GCS
# To view versions:
gcloud storage ls -l gs://goingmerry-stonks-terraform-state-prod/terraform/state/

# To restore a previous version:
gcloud storage cp gs://goingmerry-stonks-terraform-state-prod/terraform/state/default.tfstate#VERSION ./terraform.tfstate.backup
```

### Rollback Deployment

```bash
# Rollback to previous image
gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.0.0 \
  --region=us-east5
```

## Cleanup (Destroy Infrastructure)

**WARNING: This will delete all resources!**

```bash
cd terraform/environments/prod

# Plan destruction
terraform plan -destroy -out=destroy.tfplan

# Review the plan carefully
terraform show destroy.tfplan

# Destroy infrastructure
terraform destroy

# Or apply the destroy plan
terraform apply destroy.tfplan

# Manually delete the state bucket (not managed by Terraform)
gcloud storage rm -r gs://goingmerry-stonks-terraform-state-prod
```

## Troubleshooting

### SSL Certificate Not Provisioning

```bash
# Check DNS propagation
dig app.goingmerry-stonks.com +short

# Check certificate status
gcloud compute ssl-certificates describe prod-ssl-cert --global

# Common issues:
# - DNS not propagated (wait 15-60 minutes)
# - Wrong DNS record (check A record points to LB IP)
# - CAA records blocking issuance
```

### Cloud Run Deployment Fails

```bash
# Check service logs
gcloud run services logs read prod-backend-api --region=us-east5 --limit=100

# Check service configuration
gcloud run services describe prod-backend-api --region=us-east5

# Common issues:
# - Missing environment variables
# - Secret access denied (check IAM permissions)
# - Image not found (verify image was pushed)
```

### High Costs

```bash
# View cost breakdown
gcloud billing accounts list
gcloud billing account get-iam-policy BILLING_ACCOUNT_ID

# To reduce costs:
# 1. Set min_instances = 0 (scale to zero)
# 2. Disable CDN if not needed
# 3. Reduce log sampling rate
# 4. Use request-based billing instead of time-based
```

## Cost Estimation

**Expected monthly costs (production):**

| Resource | Cost Estimate |
|----------|--------------|
| Cloud Run (Backend) | $10-30/month |
| Cloud Run (Frontend) | $5-15/month |
| Load Balancer | $18/month (fixed) |
| Cloud Armor | $5-20/month |
| Artifact Registry | $0.10/GB/month |
| Secret Manager | $0.06/secret/month |
| **Total** | **~$40-90/month** |

*Costs vary based on traffic volume and resource usage*

## Support

For issues or questions:
1. Check Cloud Run logs
2. Review Terraform plan output
3. Consult GCP documentation
4. Contact your GCP support team

## Next Steps

1. ✅ Set up monitoring dashboards
2. ✅ Configure automated backups
3. ✅ Implement blue-green deployments
4. ✅ Set up staging environment (duplicate terraform/environments/prod → staging)
5. ✅ Configure custom domain with SSL
6. ✅ Set up continuous deployment with Cloud Build or GitHub Actions
