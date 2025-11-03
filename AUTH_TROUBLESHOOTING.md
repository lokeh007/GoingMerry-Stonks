# GCP Authentication Troubleshooting Guide

## The Issue

You're running `gcloud auth login` in a **headless/SSH/remote environment** where:
- No graphical browser is available
- The command tries to open a browser and fails
- Error: "Operation not supported" or browser won't launch

## ✅ **Quick Solutions**

### **Solution 1: Use `--no-launch-browser` Flag (Easiest)**

```bash
# Step 1: Authenticate with no-browser mode
gcloud auth login --no-launch-browser
```

**What happens:**
1. A URL will be displayed in the terminal
2. **Copy the entire URL**
3. **Open it in a browser on your LOCAL computer** (Windows/Mac)
4. Sign in with your Google account
5. You'll get a verification code
6. **Copy the code and paste it back in the terminal**

```bash
# Step 2: Set the project
gcloud config set project sylvan-earth-477020-u6

# Step 3: Set up Application Default Credentials (for Terraform)
gcloud auth application-default login --no-launch-browser
```

**Or use the helper script:**
```bash
./auth-headless.sh
```

---

### **Solution 2: Use Service Account (For CI/CD or Automation)**

This is better for automated deployments:

#### **Create Service Account:**

1. **Go to GCP Console:** https://console.cloud.google.com/
2. **Navigate to:** IAM & Admin → Service Accounts
3. **Click:** "Create Service Account"
   - Name: `terraform-deployment`
   - Description: `Service account for Terraform deployments`
4. **Grant Roles:**
   - `Editor` (or more specific roles)
   - `Cloud Run Admin`
   - `Cloud SQL Admin`
   - `Artifact Registry Admin`
   - `Secret Manager Admin`
5. **Create Key:**
   - Click on the service account
   - Go to "Keys" tab
   - "Add Key" → "Create new key" → JSON
   - Download the JSON file

#### **Use Service Account:**

```bash
# Transfer the key file to your server (example)
scp ~/Downloads/service-account-key.json user@your-server:~/

# On the server, authenticate
gcloud auth activate-service-account \
  --key-file=~/service-account-key.json

# Set project
gcloud config set project sylvan-earth-477020-u6

# For Terraform (Application Default Credentials)
export GOOGLE_APPLICATION_CREDENTIALS=~/service-account-key.json
```

**Security Warning:** Never commit the JSON key to git! Add to `.gitignore`:
```bash
echo "service-account-key.json" >> .gitignore
echo "*.json" >> .gitignore  # Or be more specific
```

---

### **Solution 3: Copy Credentials from Another Machine**

If you've already authenticated on your local computer:

```bash
# On your LOCAL machine (where gcloud works)
tar czf gcloud-creds.tar.gz ~/.config/gcloud/

# Transfer to remote server
scp gcloud-creds.tar.gz user@remote-server:~/

# On REMOTE server
cd ~
tar xzf gcloud-creds.tar.gz
rm gcloud-creds.tar.gz

# Verify
gcloud auth list
gcloud config get-value project
```

---

### **Solution 4: Use gcloud in Docker (Alternative)**

Run gcloud commands from a container with volume mounting:

```bash
docker run -it \
  -v ~/.config/gcloud:/root/.config/gcloud \
  google/cloud-sdk:latest \
  gcloud auth login --no-launch-browser
```

---

## 🔧 **Step-by-Step: Recommended Approach**

### **For Interactive Use (Development):**

```bash
# 1. Authenticate (no browser)
gcloud auth login --no-launch-browser

# When prompted:
# - Copy the URL
# - Open in your LOCAL browser
# - Sign in
# - Copy the code
# - Paste back in terminal

# 2. Set project
gcloud config set project sylvan-earth-477020-u6

# 3. Setup Application Default Credentials (for Terraform)
gcloud auth application-default login --no-launch-browser

# Again, copy URL, open in browser, get code, paste

# 4. Verify
gcloud auth list
gcloud config list
```

### **For Automation/CI/CD:**

Use a service account (Solution 2 above).

---

## ✅ **Verification Commands**

After authentication, verify everything works:

```bash
# Check authenticated accounts
gcloud auth list

# Check current project
gcloud config get-value project

# Check application default credentials exist
ls -la ~/.config/gcloud/application_default_credentials.json

# Test API access
gcloud projects describe sylvan-earth-477020-u6

# Test storage access
gcloud storage buckets list

# Test compute access
gcloud compute regions list --limit=5
```

---

## 🚀 **Ready to Deploy?**

Once authenticated, proceed with deployment:

```bash
# Option 1: Use deployment script
./deploy.sh

# Option 2: Manual Terraform
cd terraform/environments/prod
terraform init
terraform plan
```

---

## 🐛 **Common Issues**

### Issue: "You do not currently have an active account selected"

**Fix:**
```bash
gcloud auth login --no-launch-browser
```

### Issue: "Default credentials not found"

**Fix:**
```bash
gcloud auth application-default login --no-launch-browser
```

### Issue: "Permission denied" when accessing APIs

**Fix:**
```bash
# Ensure you're using the correct project
gcloud config set project sylvan-earth-477020-u6

# Ensure account has proper permissions
gcloud projects get-iam-policy sylvan-earth-477020-u6
```

### Issue: "API not enabled"

**Fix:**
```bash
# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

---

## 📋 **Environment Variables for Terraform**

If using a service account:

```bash
# Add to ~/.bashrc or ~/.zshrc
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
export GOOGLE_PROJECT="sylvan-earth-477020-u6"
export GOOGLE_REGION="us-east5"

# Reload
source ~/.bashrc
```

---

## 🔐 **Security Best Practices**

1. **Never commit credentials to git**
   - Service account keys
   - `~/.config/gcloud/` directory
   
2. **Use service accounts for CI/CD**
   - Not personal accounts
   
3. **Rotate service account keys regularly**
   - Every 90 days recommended
   
4. **Use least privilege**
   - Only grant necessary permissions
   
5. **Enable audit logging**
   - Track who does what

---

## 📚 **Additional Resources**

- **gcloud auth docs:** https://cloud.google.com/sdk/gcloud/reference/auth
- **Service accounts:** https://cloud.google.com/iam/docs/service-accounts
- **Workload Identity:** https://cloud.google.com/iam/docs/workload-identity-federation

---

## 🆘 **Still Having Issues?**

Run diagnostics:
```bash
# Check gcloud version
gcloud version

# Check gcloud info
gcloud info

# Check network connectivity
ping -c 3 accounts.google.com
ping -c 3 cloudresourcemanager.googleapis.com

# Check config
gcloud config list
```

**If all else fails:** Use a service account (Solution 2)
