#!/bin/bash
set -euo pipefail

# GoingMerry-Stonks Terraform Deployment Script
# This script guides you through deploying the infrastructure to GCP

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
STATE_BUCKET="goingmerry-stonks-terraform-state-prod"
TERRAFORM_DIR="terraform/environments/prod"

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    check_command "gcloud"
    print_success "gcloud CLI installed"
    
    check_command "terraform"
    print_success "Terraform installed"
    
    check_command "docker"
    print_success "Docker installed"
    
    # Check Terraform version
    TERRAFORM_VERSION=$(terraform version -json | grep -o '"terraform_version":"[^"]*' | cut -d'"' -f4)
    print_info "Terraform version: $TERRAFORM_VERSION"
}

# Authenticate with GCP
authenticate_gcp() {
    print_header "Authenticating with GCP"
    
    # Check if already authenticated
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
    
    if [[ "$CURRENT_PROJECT" != "$PROJECT_ID" ]]; then
        print_warning "Current project is not set to $PROJECT_ID"
        read -p "Do you want to authenticate now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            gcloud auth login
            gcloud config set project "$PROJECT_ID"
            gcloud auth application-default login
        else
            print_error "Authentication required. Exiting."
            exit 1
        fi
    fi
    
    print_success "Authenticated with project: $PROJECT_ID"
}

# Create state bucket
create_state_bucket() {
    print_header "Setting Up Terraform State Bucket"
    
    if gcloud storage buckets describe "gs://$STATE_BUCKET" &>/dev/null; then
        print_success "State bucket already exists: gs://$STATE_BUCKET"
    else
        print_info "Creating state bucket: gs://$STATE_BUCKET"
        
        gcloud storage buckets create "gs://$STATE_BUCKET" \
            --location="$REGION" \
            --uniform-bucket-level-access \
            --public-access-prevention
        
        gcloud storage buckets update "gs://$STATE_BUCKET" --versioning
        
        print_success "State bucket created successfully"
    fi
}

# Enable required APIs
enable_apis() {
    print_header "Enabling Required APIs"
    
    APIS=(
        "cloudbilling.googleapis.com"
        "cloudresourcemanager.googleapis.com"
        "compute.googleapis.com"
        "run.googleapis.com"
        "artifactregistry.googleapis.com"
        "secretmanager.googleapis.com"
        "sqladmin.googleapis.com"
    )
    
    for api in "${APIS[@]}"; do
        print_info "Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID" 2>/dev/null || true
    done
    
    print_success "APIs enabled"
}

# Initialize Terraform
init_terraform() {
    print_header "Initializing Terraform"
    
    cd "$TERRAFORM_DIR"
    
    terraform init
    
    print_success "Terraform initialized"
}

# Validate Terraform configuration
validate_terraform() {
    print_header "Validating Terraform Configuration"
    
    cd "$TERRAFORM_DIR"
    
    terraform validate
    terraform fmt -recursive
    
    print_success "Configuration is valid"
}

# Plan Terraform changes
plan_terraform() {
    print_header "Planning Infrastructure Changes"
    
    cd "$TERRAFORM_DIR"
    
    terraform plan -out=tfplan
    
    print_success "Plan created: tfplan"
    print_warning "Review the plan above carefully before applying"
}

# Apply Terraform
apply_terraform() {
    print_header "Applying Infrastructure Changes"
    
    cd "$TERRAFORM_DIR"
    
    read -p "Do you want to apply the Terraform plan? (yes/no): " -r
    echo
    if [[ $REPLY != "yes" ]]; then
        print_warning "Apply cancelled"
        exit 0
    fi
    
    terraform apply tfplan
    
    print_success "Infrastructure deployed successfully"
}

# Build and push Docker image
build_and_push_image() {
    print_header "Building and Pushing Backend Image"
    
    cd "$TERRAFORM_DIR"
    BACKEND_REPO=$(terraform output -raw backend_artifact_registry_url)
    
    print_info "Backend repository: $BACKEND_REPO"
    
    # Configure Docker authentication
    gcloud auth configure-docker "${REGION}-docker.pkg.dev"
    
    # Build image
    cd "../../../backend"
    print_info "Building Docker image..."
    docker build -t "${BACKEND_REPO}/api:v1.0.0" -t "${BACKEND_REPO}/api:latest" .
    
    # Push images
    print_info "Pushing Docker images..."
    docker push "${BACKEND_REPO}/api:v1.0.0"
    docker push "${BACKEND_REPO}/api:latest"
    
    print_success "Backend image built and pushed"
}

# Update Cloud Run service
update_cloud_run() {
    print_header "Updating Cloud Run Service"
    
    cd "$TERRAFORM_DIR"
    BACKEND_REPO=$(terraform output -raw backend_artifact_registry_url)
    
    gcloud run services update prod-backend-api \
        --image="${BACKEND_REPO}/api:v1.0.0" \
        --region="$REGION" \
        --project="$PROJECT_ID"
    
    print_success "Cloud Run service updated"
}

# Verify deployment
verify_deployment() {
    print_header "Verifying Deployment"
    
    cd "$TERRAFORM_DIR"
    
    BACKEND_URL=$(gcloud run services describe prod-backend-api --region="$REGION" --format='value(status.url)')
    
    print_info "Backend URL: $BACKEND_URL"
    print_info "Testing health endpoint..."
    
    if curl -s "${BACKEND_URL}/health" | grep -q "healthy"; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
    fi
    
    # Show outputs
    print_info "\nTerraform Outputs:"
    terraform output
}

# Show costs
show_costs() {
    print_header "Estimated Monthly Costs"
    
    echo "Cloud Run (Backend):     $15-40"
    echo "Cloud SQL (HA):          $150-200"
    echo "Load Balancer:           $18"
    echo "Cloud Armor:             $10-20"
    echo "VPC Connector:           $8"
    echo "Other services:          $5-10"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Total:                   ~$200-300/month"
    echo ""
    print_warning "Actual costs may vary based on usage"
}

# Main menu
show_menu() {
    echo -e "\n${BLUE}GoingMerry-Stonks Terraform Deployment${NC}\n"
    echo "1. Full Deployment (All Steps)"
    echo "2. Prerequisites Check"
    echo "3. Setup (Auth + State Bucket + APIs)"
    echo "4. Terraform Init"
    echo "5. Terraform Plan"
    echo "6. Terraform Apply"
    echo "7. Build & Push Docker Image"
    echo "8. Update Cloud Run"
    echo "9. Verify Deployment"
    echo "10. Show Estimated Costs"
    echo "11. Show Outputs"
    echo "12. Destroy Infrastructure"
    echo "0. Exit"
    echo ""
}

# Full deployment
full_deployment() {
    check_prerequisites
    authenticate_gcp
    create_state_bucket
    enable_apis
    init_terraform
    validate_terraform
    plan_terraform
    apply_terraform
    build_and_push_image
    update_cloud_run
    verify_deployment
    show_costs
    
    print_header "Deployment Complete!"
    print_success "Your infrastructure is ready"
    print_info "Next steps:"
    echo "  - Configure custom domain (optional)"
    echo "  - Set up CI/CD pipeline"
    echo "  - Review monitoring dashboards"
}

# Destroy infrastructure
destroy_infrastructure() {
    print_header "Destroying Infrastructure"
    
    print_error "WARNING: This will DELETE ALL resources and data!"
    read -p "Type 'destroy' to confirm: " -r
    echo
    
    if [[ $REPLY != "destroy" ]]; then
        print_warning "Destroy cancelled"
        return
    fi
    
    cd "$TERRAFORM_DIR"
    terraform destroy
    
    print_success "Infrastructure destroyed"
}

# Show outputs
show_outputs() {
    cd "$TERRAFORM_DIR"
    terraform output
}

# Main function
main() {
    # Change to script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"
    
    if [[ $# -eq 0 ]]; then
        # Interactive mode
        while true; do
            show_menu
            read -p "Select an option: " choice
            case $choice in
                1) full_deployment ;;
                2) check_prerequisites ;;
                3) authenticate_gcp; create_state_bucket; enable_apis ;;
                4) init_terraform ;;
                5) validate_terraform; plan_terraform ;;
                6) apply_terraform ;;
                7) build_and_push_image ;;
                8) update_cloud_run ;;
                9) verify_deployment ;;
                10) show_costs ;;
                11) show_outputs ;;
                12) destroy_infrastructure ;;
                0) exit 0 ;;
                *) print_error "Invalid option" ;;
            esac
        done
    else
        # Command line mode
        case "$1" in
            deploy) full_deployment ;;
            init) init_terraform ;;
            plan) plan_terraform ;;
            apply) apply_terraform ;;
            build) build_and_push_image ;;
            update) update_cloud_run ;;
            verify) verify_deployment ;;
            destroy) destroy_infrastructure ;;
            outputs) show_outputs ;;
            *) 
                echo "Usage: $0 [deploy|init|plan|apply|build|update|verify|destroy|outputs]"
                exit 1
                ;;
        esac
    fi
}

main "$@"
