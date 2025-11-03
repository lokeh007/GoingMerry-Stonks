# Quick Start: Deploy GoingMerry-Stonks to GCP

## 🚀 Fastest Path to Deployment

### Option 1: Interactive Script (Recommended)

```bash
# Run the deployment script
./deploy.sh

# Select option 1 for full deployment
# The script will guide you through each step
```

### Option 2: Manual Step-by-Step

```bash
# 1. Authenticate
gcloud auth login
gcloud config set project sylvan-earth-477020-u6
gcloud auth application-default login

# 2. Create state bucket
gcloud storage buckets create gs://goingmerry-stonks-terraform-state-prod \
  --location=us-east5 \
  --uniform-bucket-level-access \
  --public-access-prevention

gcloud storage buckets update gs://goingmerry-stonks-terraform-state-prod --versioning

# 3. Deploy infrastructure
cd terraform/environments/prod
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# 4. Build and deploy backend
cd ../../../
BACKEND_REPO=$(cd terraform/environments/prod && terraform output -raw backend_artifact_registry_url)
gcloud auth configure-docker us-east5-docker.pkg.dev

cd backend
docker build -t ${BACKEND_REPO}/api:v1.0.0 .
docker push ${BACKEND_REPO}/api:v1.0.0

gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.0.0 \
  --region=us-east5

# 5. Verify
curl $(gcloud run services describe prod-backend-api --region=us-east5 --format='value(status.url)')/health
```

### Option 3: Individual Commands

```bash
# Check prerequisites
./deploy.sh
# Choose option 2

# Just deploy
./deploy.sh deploy

# Just build and push
./deploy.sh build

# Just verify
./deploy.sh verify
```

## 📋 What Gets Deployed

| Resource | Description | Cost/Month |
|----------|-------------|-----------|
| **Cloud Run (Backend)** | FastAPI application | $15-40 |
| **Cloud SQL PostgreSQL** | Database (HA, 2 vCPU, 8GB) | $150-200 |
| **Load Balancer** | HTTPS + routing | $18 |
| **Cloud Armor** | WAF + DDoS protection | $10-20 |
| **VPC + Connector** | Private networking | $8 |
| **Artifact Registry** | Docker images | $1-5 |
| **Secret Manager** | API keys | $0.30 |
| **Monitoring** | Alerts + logging | Included |
| **TOTAL** | | **~$200-300** |

## 🔧 Configuration Files

- **`terraform/environments/prod/terraform.tfvars`** - Your configuration (✅ Already created)
- **`deploy.sh`** - Automated deployment script
- **`DEPLOYMENT_CHECKLIST.md`** - Detailed checklist

## ⚡ Quick Commands

```bash
# View all infrastructure outputs
cd terraform/environments/prod
terraform output

# Get backend URL
terraform output -raw backend_service_url

# Get load balancer IP
terraform output -raw load_balancer_ip

# View logs
gcloud run services logs read prod-backend-api --region=us-east5 --limit=50

# Scale up/down
# Edit terraform.tfvars: backend_min_instances = 2
terraform apply

# Rollback
gcloud run services update prod-backend-api \
  --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:v1.0.0 \
  --region=us-east5
```

## 🎯 Success Checklist

After deployment, verify:

- [ ] `terraform apply` completed without errors
- [ ] Backend image pushed to Artifact Registry
- [ ] Cloud Run service is running: `gcloud run services list --region=us-east5`
- [ ] Health endpoint responds: `curl <BACKEND_URL>/health`
- [ ] Load balancer accessible: `curl http://<LB_IP>/health`
- [ ] Database instance active: `gcloud sql instances list`
- [ ] Monitoring alerts configured: `gcloud alpha monitoring policies list`

## 🐛 Troubleshooting

### "State bucket not found"
```bash
gcloud storage buckets create gs://goingmerry-stonks-terraform-state-prod \
  --location=us-east5 --uniform-bucket-level-access --public-access-prevention
```

### "API not enabled"
```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
```

### "Permission denied"
```bash
gcloud auth application-default login
```

### "Docker push failed"
```bash
gcloud auth configure-docker us-east5-docker.pkg.dev
```

## 📊 Monitoring

- **Cloud Run**: https://console.cloud.google.com/run?project=sylvan-earth-477020-u6
- **Cloud SQL**: https://console.cloud.google.com/sql?project=sylvan-earth-477020-u6
- **Logs**: https://console.cloud.google.com/logs?project=sylvan-earth-477020-u6
- **Monitoring**: https://console.cloud.google.com/monitoring?project=sylvan-earth-477020-u6

## 💰 Cost Optimization (Optional)

For dev/testing, reduce costs by editing `terraform.tfvars`:

```hcl
backend_min_instances = 0           # Scale to zero
database_high_availability = false  # Disable HA
database_tier = "db-custom-1-4096" # Smaller tier
enable_cloud_armor = false         # Disable WAF
```

Then run: `terraform apply`

## 🗑️ Cleanup

```bash
cd terraform/environments/prod
terraform destroy
gcloud storage rm -r gs://goingmerry-stonks-terraform-state-prod
```

## 📚 More Documentation

- **Full guide**: `DEPLOYMENT_CHECKLIST.md`
- **Architecture**: `terraform/README.md`
- **Detailed steps**: `terraform/DEPLOYMENT.md`

---

**Ready to deploy?** Run: `./deploy.sh`
