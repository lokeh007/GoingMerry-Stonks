#!/bin/bash
set -e

# Configuration
PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
REPOSITORY="prod-backend"
IMAGE_NAME="api"
VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "v1.0.0")
FULL_IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${VERSION}"
LATEST_IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest"

echo "======================================"
echo "Building and Pushing Backend Image"
echo "======================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Repository: ${REPOSITORY}"
echo "Image: ${FULL_IMAGE_PATH}"
echo ""

# Configure Docker authentication
echo "Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Build the Docker image
echo ""
echo "Building Docker image..."
cd backend
docker build -t ${FULL_IMAGE_PATH} -t ${LATEST_IMAGE_PATH} .

# Push to Artifact Registry
echo ""
echo "Pushing images to Artifact Registry..."
docker push ${FULL_IMAGE_PATH}
docker push ${LATEST_IMAGE_PATH}

echo ""
echo "======================================"
echo "✓ Images successfully built and pushed!"
echo "======================================"
echo "Versioned: ${FULL_IMAGE_PATH}"
echo "Latest:    ${LATEST_IMAGE_PATH}"
echo ""
echo "Next steps:"
echo "  1. Update Terraform to use image version: ${VERSION}"
echo "  2. Run 'cd terraform/environments/prod && terraform apply' to deploy"
