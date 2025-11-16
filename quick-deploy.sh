#!/bin/bash
set -e

# Configuration
PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
REPOSITORY="prod-backend"

# Get version from argument or git
VERSION=${1:-$(git rev-parse --short HEAD 2>/dev/null || echo "latest")}

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "=========================================="
echo "Quick Deploy - GoingMerry-Stonks"
echo "=========================================="
echo ""
echo "Version: ${VERSION}"
echo ""

# Construct image paths
API_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/api:${VERSION}"
DAILY_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/daily-screeners:${VERSION}"
SMART_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/smart-money-screeners:${VERSION}"

echo "Images to deploy:"
echo "  API:          ${API_IMAGE}"
echo "  Daily:        ${DAILY_IMAGE}"
echo "  Smart Money:  ${SMART_IMAGE}"
echo ""

# Update Backend API
echo -e "${GREEN}[1/11]${NC} Updating backend API..."
gcloud run services update prod-backend-api \
  --image="${API_IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet

# Update Regular Screener Jobs (5 jobs)
for batch in {1..5}; do
  echo -e "${GREEN}[$((batch + 1))/11]${NC} Updating regular screeners batch ${batch}..."
  gcloud run jobs update "prod-regular-screeners-batch-${batch}" \
    --image="${DAILY_IMAGE}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet
done

# Update Smart Money Screener Jobs (5 jobs)
for batch in {1..5}; do
  echo -e "${GREEN}[$((batch + 6))/11]${NC} Updating smart money screeners batch ${batch}..."
  gcloud run jobs update "prod-smart-money-screeners-batch-${batch}" \
    --image="${SMART_IMAGE}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet
done

echo ""
echo -e "${GREEN}=========================================="
echo "✓ Deployment Complete! 🚀"
echo "==========================================${NC}"
echo ""
echo "All 11 services/jobs updated with: ${VERSION}"
echo ""
echo "Verify:"
echo "  Backend API: https://prod-backend-api-rlfl2vcoda-ul.a.run.app/api/docs"
echo "  Frontend:    https://goingmerry-stonks.web.app"
echo ""
echo "Monitor logs:"
echo "  gcloud run services logs tail prod-backend-api --region=${REGION}"
echo ""
