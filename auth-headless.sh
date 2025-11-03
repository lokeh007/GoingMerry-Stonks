#!/bin/bash
# GCP Authentication Guide for Headless/Remote Environments

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  GCP Authentication for Remote/Headless Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}You're running in a headless environment (no browser).${NC}\n"

echo -e "${GREEN}Method 1: Browser-less Authentication (Recommended)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Run this command:"
echo -e "${BLUE}gcloud auth login --no-launch-browser${NC}\n"
echo "Steps:"
echo "1. Copy the URL that appears"
echo "2. Open it in a browser on your LOCAL machine"
echo "3. Sign in to your Google account"
echo "4. Copy the verification code"
echo "5. Paste it back in the terminal"
echo ""

echo -e "${GREEN}Method 2: Service Account (For Automation)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Create a service account in GCP Console"
echo "2. Download the JSON key"
echo "3. Run:"
echo -e "${BLUE}gcloud auth activate-service-account --key-file=path/to/key.json${NC}"
echo ""

echo -e "${GREEN}Method 3: Use Existing Credentials${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "If you've already authenticated on another machine:"
echo "1. Copy credentials from ~/.config/gcloud/"
echo "2. Transfer to this machine"
echo ""

read -p "Press Enter to start browser-less authentication..." 

echo -e "\n${BLUE}Starting authentication...${NC}\n"
gcloud auth login --no-launch-browser

echo -e "\n${GREEN}✓ Authentication complete!${NC}\n"

echo "Setting project..."
gcloud config set project sylvan-earth-477020-u6

echo -e "\n${BLUE}Setting up Application Default Credentials...${NC}"
echo "This is needed for Terraform to work."
echo ""
gcloud auth application-default login --no-launch-browser

echo -e "\n${GREEN}✓ All authentication complete!${NC}"
echo ""
echo "Verify with:"
echo -e "${BLUE}gcloud auth list${NC}"
echo -e "${BLUE}gcloud config get-value project${NC}"
