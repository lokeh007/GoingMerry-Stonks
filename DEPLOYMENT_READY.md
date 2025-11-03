# 🚀 GoingMerry-Stonks - GCP Terraform Deployment Ready

## ✅ Setup Complete

Your Terraform deployment is now ready! Here's what's been prepared:

### 📁 Files Created/Updated

1. **`terraform/environments/prod/terraform.tfvars`** ✅
   - Pre-configured with your project settings
   - Contains API keys (DO NOT commit to git)
   
2. **`deploy.sh`** ✅
   - Automated deployment script with interactive menu
   - Handles entire deployment workflow
   
3. **`QUICKSTART.md`** ✅
   - Quick reference for deployment commands
   - Troubleshooting guide
   
4. **`DEPLOYMENT_CHECKLIST.md`** ✅
   - Comprehensive step-by-step guide
   - Detailed verification steps
   
5. **`.gitignore`** ✅
   - Updated to exclude sensitive Terraform files
   - Protects `terraform.tfvars` from being committed

### 🎯 Your Next Steps

#### **Option 1: Fully Automated (Recommended)**

```bash
# Run interactive deployment script
./deploy.sh

# Select option 1 for full deployment
# The script will guide you through:
# ✓ Authentication
# ✓ State bucket creation
# ✓ API enablement
# ✓ Terraform init/plan/apply
# ✓ Docker build and push
# ✓ Cloud Run deployment
# ✓ Verification
```

#### **Option 2: Quick Manual Deployment**

```bash
# 1. Authenticate (required first)
gcloud auth login
gcloud config set project sylvan-earth-477020-u6
gcloud auth application-default login

# 2. Create state bucket (one-time)
gcloud storage buckets create gs://goingmerry-stonks-terraform-state-prod \
  --location=us-east5 \
  --uniform-bucket-level-access \
  --public-access-prevention

gcloud storage buckets update gs://goingmerry-stonks-terraform-state-prod --versioning

# 3. Deploy infrastructure (15-20 minutes)
cd terraform/environments/prod
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# 4. Build and push backend
cd ../../../
BACKEND_REPO=$(cd terraform/environments/prod && terraform output -raw backend_artifact_registry_url)
gcloud auth configure-docker us-east5-docker.pkg.dev

cd backend
docker build -t ${BACKEND_REPO}/api:v1.0.0 .
docker push ${BACKEND_REPO}/api:v1.0.0

# 5. Deploy to Cloud Run
gcloud run services update prod-backend-api \
  --image=${BACKEND_REPO}/api:v1.0.0 \
  --region=us-east5

# 6. Verify
curl $(gcloud run services describe prod-backend-api --region=us-east5 --format='value(status.url)')/health
```

### 📊 What Will Be Deployed

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend API** | Cloud Run + FastAPI | Serverless container for API |
| **Database** | Cloud SQL PostgreSQL 15 | Managed relational database (HA) |
| **Load Balancer** | Cloud Load Balancing | HTTPS termination + routing |
| **Security** | Cloud Armor | WAF + DDoS protection |
| **Secrets** | Secret Manager | Encrypted credential storage |
| **Registry** | Artifact Registry | Docker image storage |
| **VPC** | VPC + Serverless Connector | Private database connectivity |
| **Monitoring** | Cloud Monitoring | Alerts + metrics |

### 💰 Estimated Costs

**Production Configuration**: ~$200-300/month
- Cloud Run: $15-40
- Cloud SQL (HA): $150-200
- Load Balancer: $18
- Cloud Armor: $10-20
- VPC Connector: $8
- Others: $5-10

**To reduce costs** (dev/testing), edit `terraform/environments/prod/terraform.tfvars`:
```hcl
backend_min_instances = 0           # Scale to zero
database_high_availability = false  # Disable HA
database_tier = "db-custom-1-4096" # Smaller tier (1 vCPU, 4GB)
enable_cloud_armor = false         # Disable WAF
```

### 🔐 Security Notes

✅ **Already Configured:**
- Private IP for Cloud SQL
- Secret Manager for API keys
- Service account with least privilege
- Cloud Armor with rate limiting
- TLS/SSL encryption
- Automated backups (30 days)
- Point-in-time recovery enabled

⚠️ **Important:**
- `terraform.tfvars` contains sensitive data (excluded from git)
- Never commit API keys or secrets to version control
- State bucket has versioning enabled for safety

### 📚 Documentation Reference

- **Quick Start**: `QUICKSTART.md` - Fast deployment guide
- **Checklist**: `DEPLOYMENT_CHECKLIST.md` - Detailed step-by-step
- **Architecture**: `terraform/README.md` - Infrastructure overview
- **Deployment**: `terraform/DEPLOYMENT.md` - Complete deployment guide

### 🔧 Useful Commands

```bash
# View infrastructure outputs
cd terraform/environments/prod && terraform output

# Check deployment status
gcloud run services list --region=us-east5

# View logs
gcloud run services logs read prod-backend-api --region=us-east5 --limit=50

# Access GCP Console
# Cloud Run: https://console.cloud.google.com/run?project=sylvan-earth-477020-u6
# Cloud SQL: https://console.cloud.google.com/sql?project=sylvan-earth-477020-u6
# Logs: https://console.cloud.google.com/logs?project=sylvan-earth-477020-u6

# Rollback deployment
gcloud run services update prod-backend-api \
  --image=us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/api:v1.0.0 \
  --region=us-east5

# Destroy everything (CAUTION)
cd terraform/environments/prod && terraform destroy
```

### ✨ Deployment Timeline

| Step | Duration | Description |
|------|----------|-------------|
| 1. Authentication | 2-3 min | gcloud login + setup |
| 2. State bucket | 1 min | One-time creation |
| 3. Terraform init | 1-2 min | Provider download |
| 4. Terraform apply | 15-20 min | Infrastructure creation |
| 5. Docker build | 3-5 min | Backend image build |
| 6. Docker push | 2-3 min | Upload to registry |
| 7. Cloud Run update | 1-2 min | Deploy new image |
| **Total** | **~25-35 min** | First deployment |

Subsequent deployments: ~5-10 minutes (infrastructure already exists)

### 🎯 Success Criteria

After deployment, you should have:

- ✅ Terraform state stored in GCS bucket
- ✅ All GCP APIs enabled
- ✅ Cloud Run service responding to health checks
- ✅ Database instance running with HA
- ✅ Load balancer routing traffic
- ✅ Monitoring alerts configured
- ✅ Docker images in Artifact Registry
- ✅ Secrets stored in Secret Manager

### 🐛 Common Issues & Solutions

**Issue**: "You do not currently have an active account selected"
```bash
gcloud auth login
gcloud auth application-default login
```

**Issue**: "State bucket does not exist"
```bash
gcloud storage buckets create gs://goingmerry-stonks-terraform-state-prod \
  --location=us-east5 --uniform-bucket-level-access --public-access-prevention
```

**Issue**: "API not enabled"
```bash
gcloud services enable <api-name>
# Example: gcloud services enable run.googleapis.com
```

**Issue**: "Docker push denied"
```bash
gcloud auth configure-docker us-east5-docker.pkg.dev
```

### 🚦 Ready to Deploy?

**Choose your deployment method:**

1. **Interactive (Easiest)**: `./deploy.sh`
2. **Quick manual**: See commands above
3. **Step-by-step**: Follow `DEPLOYMENT_CHECKLIST.md`

### 📞 Support

If you encounter issues:
1. Check the logs: `gcloud run services logs read prod-backend-api --region=us-east5`
2. Review Terraform output: `cd terraform/environments/prod && terraform output`
3. Verify APIs enabled: `gcloud services list --enabled`
4. Check GCP Console: https://console.cloud.google.com/

---

**Project**: GoingMerry-Stonks  
**Environment**: Production  
**Region**: us-east5  
**Project ID**: sylvan-earth-477020-u6  

**Status**: ✅ READY TO DEPLOY

Run `./deploy.sh` to get started! 🚀
