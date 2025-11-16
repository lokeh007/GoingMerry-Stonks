#!/bin/bash
set -e

# Save project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
REPOSITORY="prod-backend"
VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")

echo "=========================================="
echo "Building and Pushing ALL Backend Images"
echo "=========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Repository: ${REPOSITORY}"
echo "Version: ${VERSION}"
echo ""

# Configure Docker authentication
echo "Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

cd backend

# ============================================
# 1. Build and Push API Image
# ============================================
echo ""
echo "=========================================="
echo "Building API Image (backend)"
echo "=========================================="

API_VERSIONED="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/api:${VERSION}"
API_LATEST="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/api:latest"

docker build -t ${API_VERSIONED} -t ${API_LATEST} -f Dockerfile .

echo "Pushing API images..."
docker push ${API_VERSIONED}
docker push ${API_LATEST}

echo "✓ API images pushed successfully!"

# ============================================
# 2. Build and Push Daily Screeners Image
# ============================================
echo ""
echo "=========================================="
echo "Building Daily Screeners Image"
echo "=========================================="

DAILY_VERSIONED="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/daily-screeners:${VERSION}"
DAILY_LATEST="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/daily-screeners:latest"

docker build -t ${DAILY_VERSIONED} -t ${DAILY_LATEST} -f Dockerfile.daily_screeners .

echo "Pushing Daily Screeners images..."
docker push ${DAILY_VERSIONED}
docker push ${DAILY_LATEST}

echo "✓ Daily Screeners images pushed successfully!"

# ============================================
# 3. Build and Push Smart Money Screeners Image
# ============================================
echo ""
echo "=========================================="
echo "Building Smart Money Screeners Image"
echo "=========================================="

SMART_VERSIONED="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/smart-money-screeners:${VERSION}"
SMART_LATEST="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/smart-money-screeners:latest"

docker build -t ${SMART_VERSIONED} -t ${SMART_LATEST} -f Dockerfile.smart_money_screeners .

echo "Pushing Smart Money Screeners images..."
docker push ${SMART_VERSIONED}
docker push ${SMART_LATEST}

echo "✓ Smart Money Screeners images pushed successfully!"

# ============================================
# Summary
# ============================================
echo ""
echo "=========================================="
echo "✓ ALL IMAGES BUILT AND PUSHED!"
echo "=========================================="
echo ""
echo "API:"
echo "  - ${API_VERSIONED}"
echo "  - ${API_LATEST}"
echo ""
echo "Daily Screeners:"
echo "  - ${DAILY_VERSIONED}"
echo "  - ${DAILY_LATEST}"
echo ""
echo "Smart Money Screeners:"
echo "  - ${SMART_VERSIONED}"
echo "  - ${SMART_LATEST}"
echo ""
echo "=========================================="
echo "Deploy These Images?"
echo "=========================================="
echo ""
read -p "Deploy to production now? [y/N]: " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo ""
  echo "Running quick deployment..."
  "${PROJECT_ROOT}/quick-deploy.sh" ${VERSION}
else
  echo ""
  echo "=========================================="
  echo "Deployment Skipped - Manual Options:"
  echo "=========================================="
  echo ""
  echo "Option 1: Quick Deploy (gcloud - recommended)"
  echo "  ./quick-deploy.sh ${VERSION}"
  echo "  or:"
  echo "  ./quick-deploy.sh latest"
  echo ""
  echo "Option 2: Deploy with Terraform"
  echo "  Update terraform.tfvars:"
  echo "    backend_image = \"...api:${VERSION}\""
  echo "    docker_image = \"...daily-screeners:${VERSION}\""
  echo "    smart_money_docker_image = \"...smart-money-screeners:${VERSION}\""
  echo "  Then: cd terraform/environments/prod && terraform apply"
  echo ""
fi
