#!/bin/bash
set -e

# Configuration
PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
REPOSITORY="prod-backend"
IMAGE_NAME="api"
VERSION="v1.0.0"
FULL_IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${VERSION}"

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
docker build -t ${FULL_IMAGE_PATH} .

# Push to Artifact Registry
echo ""
echo "Pushing image to Artifact Registry..."
docker push ${FULL_IMAGE_PATH}

echo ""
echo "======================================"
echo "✓ Image successfully built and pushed!"
echo "======================================"
echo "Image: ${FULL_IMAGE_PATH}"
echo ""
echo "Next step: Run 'terraform apply -auto-approve' to deploy Cloud Run service"
