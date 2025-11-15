#!/bin/bash

# Firestore Rules Deployment Script
# This script deploys environment-specific Firestore security rules

set -euo pipefail  # Exit on error, unset variables are errors, fail on pipeline errors

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if environment argument is provided
if [ -z "${1:-}" ]; then
    print_error "Environment not specified!"
    echo ""
    echo "Usage: ./scripts/deploy-firestore-rules.sh <environment>"
    echo ""
    echo "Available environments:"
    echo "  - dev         (development)"
    echo "  - staging     (staging - not yet configured)"
    echo "  - prod        (production)"
    echo ""
    echo "Example: ./scripts/deploy-firestore-rules.sh prod"
    exit 1
fi

ENVIRONMENT="${1}"

# Determine which rules file to use
case $ENVIRONMENT in
    dev|development)
        RULES_FILE="firestore/firestore.rules.dev"
        FIREBASE_PROJECT="[UPDATE_WITH_DEV_PROJECT_ID]"
        print_warn "Development environment not fully configured!"
        print_warn "Update firestore/firestore.rules.dev with dev service account details"
        print_warn "Update FIREBASE_PROJECT in this script with dev project ID"
        ;;
    staging)
        print_error "Staging environment not yet configured!"
        print_info "To add staging: Create firestore/firestore.rules.staging and update this script"
        exit 1
        ;;
    prod|production)
        RULES_FILE="firestore/firestore.rules.prod"
        FIREBASE_PROJECT="goingmerry-stonks"
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        echo "Valid options: dev, staging, prod"
        exit 1
        ;;
esac

# Verify rules file exists
if [ ! -f "$RULES_FILE" ]; then
    print_error "Rules file not found: $RULES_FILE"
    exit 1
fi

print_info "Deploying Firestore rules for environment: $ENVIRONMENT"
print_info "Rules file: $RULES_FILE"
print_info "Firebase project: $FIREBASE_PROJECT"
echo ""

# Copy rules file to root (required by firebase.json)
print_info "Copying $RULES_FILE to firestore.rules..."
cp "$RULES_FILE" firestore.rules

# Show diff if git is available
if command -v git &> /dev/null; then
    if git diff --quiet firestore.rules; then
        print_info "No changes detected in firestore.rules"
    else
        print_warn "Changes detected in firestore.rules:"
        git diff firestore.rules
    fi
fi

# Confirm deployment
echo ""
read -p "Deploy these rules to $FIREBASE_PROJECT? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warn "Deployment cancelled"
    exit 0
fi

# Deploy rules
print_info "Deploying rules to Firebase..."
firebase deploy --only firestore:rules --project "$FIREBASE_PROJECT"

# If we reach here, deployment succeeded (set -e would have exited on failure)
print_info "✓ Firestore rules deployed successfully!"
print_info "Environment: $ENVIRONMENT"
print_info "Project: $FIREBASE_PROJECT"
