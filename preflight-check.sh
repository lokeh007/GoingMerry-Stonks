#!/bin/bash
# Pre-flight Check for GoingMerry-Stonks Terraform Deployment
# Run this before deploying to ensure everything is ready

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNINGS=0

print_check() {
    if [ "$2" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASSED++))
    elif [ "$2" = "FAIL" ]; then
        echo -e "${RED}✗${NC} $1"
        ((FAILED++))
    elif [ "$2" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $1"
        ((WARNINGS++))
    else
        echo -e "${BLUE}ℹ${NC} $1"
    fi
}

echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  GoingMerry-Stonks - Pre-Flight Check${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}\n"

# Check prerequisites
echo -e "${BLUE}1. Checking Prerequisites${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud version --format="value(Google Cloud SDK)" 2>/dev/null | head -1)
    print_check "gcloud CLI installed ($GCLOUD_VERSION)" "PASS"
else
    print_check "gcloud CLI not found" "FAIL"
fi

if command -v terraform &> /dev/null; then
    TERRAFORM_VERSION=$(terraform version -json 2>/dev/null | grep -o '"terraform_version":"[^"]*' | cut -d'"' -f4)
    print_check "Terraform installed ($TERRAFORM_VERSION)" "PASS"
    
    REQUIRED_VERSION="1.5.0"
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$TERRAFORM_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
        print_check "Terraform version >= $REQUIRED_VERSION" "PASS"
    else
        print_check "Terraform version >= $REQUIRED_VERSION (current: $TERRAFORM_VERSION)" "WARN"
    fi
else
    print_check "Terraform not found" "FAIL"
fi

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    print_check "Docker installed ($DOCKER_VERSION)" "PASS"
    
    if docker info &> /dev/null; then
        print_check "Docker daemon running" "PASS"
    else
        print_check "Docker daemon not running" "FAIL"
    fi
else
    print_check "Docker not found" "FAIL"
fi

# Check GCP authentication
echo -e "\n${BLUE}2. Checking GCP Authentication${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [ -n "$CURRENT_PROJECT" ]; then
    print_check "gcloud authenticated (project: $CURRENT_PROJECT)" "PASS"
    
    EXPECTED_PROJECT="sylvan-earth-477020-u6"
    if [ "$CURRENT_PROJECT" = "$EXPECTED_PROJECT" ]; then
        print_check "Correct project configured" "PASS"
    else
        print_check "Project mismatch (expected: $EXPECTED_PROJECT, got: $CURRENT_PROJECT)" "WARN"
    fi
else
    print_check "gcloud not authenticated" "FAIL"
fi

CURRENT_ACCOUNT=$(gcloud config get-value account 2>/dev/null || echo "")
if [ -n "$CURRENT_ACCOUNT" ]; then
    print_check "Active account: $CURRENT_ACCOUNT" "PASS"
else
    print_check "No active account" "FAIL"
fi

# Check application default credentials
if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
    print_check "Application default credentials configured" "PASS"
else
    print_check "Application default credentials not found" "WARN"
    echo "  Run: gcloud auth application-default login"
fi

# Check configuration files
echo -e "\n${BLUE}3. Checking Configuration Files${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "terraform/environments/prod/terraform.tfvars" ]; then
    print_check "terraform.tfvars exists" "PASS"
    
    # Check for required variables
    if grep -q "project_id.*sylvan-earth-477020-u6" terraform/environments/prod/terraform.tfvars; then
        print_check "project_id configured" "PASS"
    else
        print_check "project_id not set correctly" "FAIL"
    fi
    
    if grep -q "polygon_api_key.*=" terraform/environments/prod/terraform.tfvars && \
       ! grep -q "polygon_api_key.*YOUR_API_KEY" terraform/environments/prod/terraform.tfvars; then
        print_check "polygon_api_key configured" "PASS"
    else
        print_check "polygon_api_key not set" "FAIL"
    fi
    
    if grep -q "alert_email.*@" terraform/environments/prod/terraform.tfvars; then
        print_check "alert_email configured" "PASS"
    else
        print_check "alert_email not set" "WARN"
    fi
else
    print_check "terraform.tfvars not found" "FAIL"
fi

if [ -f "backend/requirements.txt" ]; then
    print_check "Backend requirements.txt exists" "PASS"
else
    print_check "Backend requirements.txt not found" "WARN"
fi

if [ -f "backend/Dockerfile" ]; then
    print_check "Backend Dockerfile exists" "PASS"
else
    print_check "Backend Dockerfile not found" "FAIL"
fi

# Check Terraform configuration
echo -e "\n${BLUE}4. Checking Terraform Configuration${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd terraform/environments/prod

if [ -f "main.tf" ]; then
    print_check "main.tf exists" "PASS"
else
    print_check "main.tf not found" "FAIL"
fi

if [ -f "variables.tf" ]; then
    print_check "variables.tf exists" "PASS"
else
    print_check "variables.tf not found" "FAIL"
fi

if [ -f "../../backend.tf" ]; then
    print_check "backend.tf exists" "PASS"
else
    print_check "backend.tf not found" "FAIL"
fi

# Check modules
MODULES=("backend" "database" "networking" "secrets")
ALL_MODULES_EXIST=true
for module in "${MODULES[@]}"; do
    if [ -f "../../modules/$module/main.tf" ]; then
        print_check "Module '$module' exists" "PASS"
    else
        print_check "Module '$module' not found" "FAIL"
        ALL_MODULES_EXIST=false
    fi
done

cd - > /dev/null

# Check state bucket
echo -e "\n${BLUE}5. Checking State Bucket${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

STATE_BUCKET="goingmerry-stonks-terraform-state-prod"
if gcloud storage buckets describe "gs://$STATE_BUCKET" &>/dev/null; then
    print_check "State bucket exists (gs://$STATE_BUCKET)" "PASS"
    
    VERSIONING=$(gcloud storage buckets describe "gs://$STATE_BUCKET" --format="value(versioning.enabled)" 2>/dev/null || echo "false")
    if [ "$VERSIONING" = "True" ]; then
        print_check "Bucket versioning enabled" "PASS"
    else
        print_check "Bucket versioning not enabled" "WARN"
    fi
else
    print_check "State bucket does not exist" "WARN"
    echo "  Create with: ./deploy.sh or manually create bucket"
fi

# Check GCP APIs
echo -e "\n${BLUE}6. Checking GCP APIs${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REQUIRED_APIS=(
    "run.googleapis.com"
    "compute.googleapis.com"
    "artifactregistry.googleapis.com"
    "secretmanager.googleapis.com"
    "sqladmin.googleapis.com"
)

if [ -n "$CURRENT_PROJECT" ]; then
    for api in "${REQUIRED_APIS[@]}"; do
        if gcloud services list --enabled --project="$CURRENT_PROJECT" 2>/dev/null | grep -q "$api"; then
            print_check "$api enabled" "PASS"
        else
            print_check "$api not enabled" "WARN"
            echo "  Enable with: gcloud services enable $api"
        fi
    done
else
    print_check "Cannot check APIs (not authenticated)" "WARN"
fi

# Check disk space
echo -e "\n${BLUE}7. Checking System Resources${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

AVAILABLE_SPACE=$(df -BG . | tail -1 | awk '{print $4}' | tr -d 'G')
if [ "$AVAILABLE_SPACE" -gt 5 ]; then
    print_check "Sufficient disk space (${AVAILABLE_SPACE}GB available)" "PASS"
else
    print_check "Low disk space (${AVAILABLE_SPACE}GB available)" "WARN"
fi

# Check network connectivity
if ping -c 1 -W 2 google.com &> /dev/null; then
    print_check "Internet connectivity" "PASS"
else
    print_check "No internet connectivity" "FAIL"
fi

# Summary
echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}\n"

echo -e "${GREEN}Passed:${NC}   $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC}   $FAILED"

echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}✗ Pre-flight check failed${NC}"
    echo -e "Please fix the issues above before deploying.\n"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠ Pre-flight check passed with warnings${NC}"
    echo -e "You can proceed, but consider addressing the warnings.\n"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    exit 0
else
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo -e "You're ready to deploy.\n"
    echo -e "Run: ${BLUE}./deploy.sh${NC}"
    echo ""
    exit 0
fi
