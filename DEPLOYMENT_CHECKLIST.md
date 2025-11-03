# GoingMerry-Stonks GCP Deployment Checklist

## Pre-Deployment Setup ✅

### 1. Authentication & Project Setup

```bash
# Re-authenticate with GCP
gcloud auth login

# Set project
gcloud config set project sylvan-earth-477020-u6

# Application default credentials (required for Terraform)
gcloud auth application-default login

# Verify authentication
gcloud config get-value project
gcloud auth list
```

### 2. Create Terraform State Bucket (One-Time)

```bash
# Create state bucket
gcloud storage buckets create gs://goingmerry-stonks-terraform-state-prod \
  --location=us-east5 \
  --uniform-bucket-level-access \
  --public-access-prevention

# Enable versioning
gcloud storage buckets update gs://goingmerry-stonks-terraform-state-prod \
  --versioning

# Verify bucket
gcloud storage buckets describe gs://goingmerry-stonks-terraform-state-prod
```

### 3. Enable Required APIs

```bash
# Enable critical APIs manually (Terraform will enable others)
gcloud services enable cloudbilling.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

## Deployment Process 🚀

### Step 1: Initialize Terraform

```bash
cd /home/nameci/projects/GoingMerry-Stonks/terraform/environments/prod

# Initialize Terraform
terraform init

# Expected output:
# - Downloads providers (google, google-beta, random)
# - Configures GCS backend
# - Success message
```

### Step 2: Validate Configuration

```bash
# Validate syntax
terraform validate

# Format files
terraform fmt -recursive

# Expected: "Success! The configuration is valid."
```

### Step 3: Plan Infrastructure

```bash
# Create execution plan
terraform plan -out=tfplan

# Review carefully:
# - ~35-40 resources will be created
# - Cloud Run services
# - Cloud SQL instance
# - Load Balancer
# - VPC and networking
# - Secret Manager secrets
# - Monitoring alerts
```

### Step 4: Apply Infrastructure (15-20 minutes)

```bash
# Apply the plan
terraform apply tfplan

# Monitor progress - wait for completion
# Most time-consuming: Cloud SQL instance creation (~10 minutes)
```

### Step 5: Build & Push Backend Docker Image

```bash
# Get artifact registry URL
cd /home/nameci/projects/GoingMerry-Stonks/terraform/environments/prod
BACKEND_REPO=$(terraform output -raw backend_artifact_registry_url)
echo "Backend Repo: ${BACKEND_REPO}"

# Configure Docker auth
gcloud auth configure-docker us-east5-docker.pkg.dev

# Build backend image
cd /home/nameci/projects/GoingMerry-Stonks/backend
docker build -t ${BACKEND_REPO}/api:v1.0.0 -t ${BACKEND_REPO}/api:latest .

# Push images
docker push ${BACKEND_REPO}/api:v1.0.0
docker push ${BACKEND_REPO}/api:latest
```

### Step 6: Update Cloud Run with Image

```bash
# Update backend service
gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.0.0 \
  --region=us-east5

# Verify deployment
gcloud run services describe prod-backend-api --region=us-east5
```

### Step 7: Verify Deployment

```bash
# Get service URLs
BACKEND_URL=$(gcloud run services describe prod-backend-api --region=us-east5 --format='value(status.url)')

# Test health endpoint
curl ${BACKEND_URL}/health

# Expected: {"status":"healthy"}

# Get load balancer IP
cd /home/nameci/projects/GoingMerry-Stonks/terraform/environments/prod
LB_IP=$(terraform output -raw load_balancer_ip)

# Test through load balancer
curl http://${LB_IP}/health
```

## Post-Deployment Tasks 📊

### Configure Monitoring

```bash
# View Cloud Run metrics
gcloud run services list --region=us-east5

# Check monitoring alerts
gcloud alpha monitoring policies list --project=sylvan-earth-477020-u6
```

### View Logs

```bash
# Backend logs
gcloud run services logs read prod-backend-api --region=us-east5 --limit=50

# Load balancer logs
gcloud logging read "resource.type=http_load_balancer" --limit=20
```

### Access Dashboards

- **Cloud Run**: https://console.cloud.google.com/run?project=sylvan-earth-477020-u6
- **Cloud SQL**: https://console.cloud.google.com/sql/instances?project=sylvan-earth-477020-u6
- **Load Balancer**: https://console.cloud.google.com/net-services/loadbalancing?project=sylvan-earth-477020-u6
- **Logs**: https://console.cloud.google.com/logs?project=sylvan-earth-477020-u6
- **Monitoring**: https://console.cloud.google.com/monitoring?project=sylvan-earth-477020-u6

## Troubleshooting 🔧

### Issue: Terraform Init Fails

```bash
# Check credentials
gcloud auth application-default login

# Verify project
gcloud config get-value project

# Check bucket exists
gcloud storage buckets describe gs://goingmerry-stonks-terraform-state-prod
```

### Issue: API Not Enabled

```bash
# Enable specific API
gcloud services enable <API_NAME>

# List enabled services
gcloud services list --enabled
```

### Issue: Docker Push Fails

```bash
# Re-configure Docker auth
gcloud auth configure-docker us-east5-docker.pkg.dev

# Verify artifact registry exists
gcloud artifacts repositories list --location=us-east5

# Check permissions
gcloud projects get-iam-policy sylvan-earth-477020-u6
```

### Issue: Cloud Run Deployment Fails

```bash
# Check Cloud Run logs
gcloud run services logs read prod-backend-api --region=us-east5 --limit=100

# Verify service configuration
gcloud run services describe prod-backend-api --region=us-east5

# Check secret access
gcloud secrets list
gcloud secrets versions access latest --secret=prod-polygon-api-key
```

### Issue: Database Connection Problems

```bash
# Check Cloud SQL instance
gcloud sql instances describe prod-postgres-* --format=json

# Verify VPC connector
gcloud compute networks vpc-access connectors describe prod-vpc-connector --region=us-east5

# Test database connectivity
gcloud sql connect INSTANCE_NAME --user=app_user
```

## Cost Optimization 💰

### Current Configuration Costs (Est. $200-300/month)

- Cloud Run: $15-40
- Cloud SQL (HA): $150-200
- Load Balancer: $18
- Cloud Armor: $10-20
- VPC Connector: $8
- Others: $5-10

### To Reduce Costs (Dev/Testing):

```hcl
# Edit terraform.tfvars
backend_min_instances = 0           # Scale to zero
database_high_availability = false  # Single instance
database_tier = "db-custom-1-4096" # Smaller tier (1 vCPU, 4GB)
enable_cloud_armor = false         # Disable WAF
log_sample_rate = 0.1              # Sample 10% of logs
```

```bash
# Apply changes
terraform apply
```

## Rollback Procedures 🔄

### Rollback Application

```bash
# Deploy previous version
gcloud run services update prod-backend-api \
  --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:v1.0.0 \
  --region=us-east5
```

### Rollback Infrastructure

```bash
# Restore previous Terraform state
cd /home/nameci/projects/GoingMerry-Stonks/terraform/environments/prod

# List state versions
gcloud storage ls -l gs://goingmerry-stonks-terraform-state-prod/terraform/state/

# Download previous version
gcloud storage cp gs://goingmerry-stonks-terraform-state-prod/terraform/state/default.tfstate#VERSION \
  ./terraform.tfstate.backup

# Use Git to rollback configuration
git checkout HEAD~1 -- *.tf
terraform apply
```

## Cleanup/Destroy 🗑️

**⚠️ WARNING: This deletes ALL resources and data!**

```bash
cd /home/nameci/projects/GoingMerry-Stonks/terraform/environments/prod

# Plan destruction
terraform plan -destroy -out=destroy.tfplan

# Review carefully
terraform show destroy.tfplan

# Destroy infrastructure
terraform apply destroy.tfplan

# Delete state bucket
gcloud storage rm -r gs://goingmerry-stonks-terraform-state-prod
```

## Quick Reference Commands

```bash
# View all outputs
terraform output

# Refresh outputs
terraform refresh

# Show current state
terraform show

# List resources
terraform state list

# Get specific output
terraform output -raw backend_service_url

# Force unlock state (if stuck)
terraform force-unlock LOCK_ID

# Import existing resource
terraform import google_compute_network.vpc projects/sylvan-earth-477020-u6/global/networks/prod-vpc
```

## CI/CD Integration (Future)

### GitHub Actions Workflow

1. Create `.github/workflows/deploy.yml`
2. Set up Workload Identity Federation
3. Configure secrets: `GCP_PROJECT_ID`, `GCP_SA_KEY`
4. Automate: `terraform plan` on PR, `terraform apply` on merge to main

### Cloud Build Trigger

```bash
# Create trigger
gcloud builds triggers create github \
  --repo-name=GoingMerry-Stonks \
  --repo-owner=lokeh007 \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --region=us-east5
```

## Success Criteria ✅

- [ ] Terraform state stored in GCS bucket
- [ ] All APIs enabled
- [ ] Infrastructure deployed successfully
- [ ] Backend Docker image built and pushed
- [ ] Cloud Run service running
- [ ] Health endpoint responding
- [ ] Load balancer accessible
- [ ] Cloud SQL instance active
- [ ] Monitoring alerts configured
- [ ] Logs flowing to Cloud Logging

## Next Steps

1. Configure custom domain and DNS
2. Set up staging environment
3. Implement CI/CD pipeline
4. Configure database backups schedule
5. Set up log-based metrics
6. Create runbooks for common operations
7. Document API endpoints
8. Set up performance testing

---

**Project**: GoingMerry-Stonks  
**Environment**: Production  
**Region**: us-east5  
**Project ID**: sylvan-earth-477020-u6  
**Documentation**: See `/terraform/README.md` and `/terraform/DEPLOYMENT.md`
