#!/bin/bash
set -e

# Setup Daily Health Check Email
#
# Sends a daily summary email at 7 AM ET with:
# - Stocks discovered per screener
# - Job execution success rates
# - Error breakdown
# - Blacklist growth
#
# Usage: ./scripts/setup-daily-email.sh

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
EMAIL="brian.boatright@gmail.com"
GMAIL_SENDER="your-email@gmail.com"  # Update this!

echo "=========================================="
echo "Daily Health Check Email Setup"
echo "=========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Recipient: ${EMAIL}"
echo "Send Time: 7:00 AM ET (12:00 PM UTC)"
echo ""

# Check if Gmail App Password is set
if [ -z "$GMAIL_APP_PASSWORD" ]; then
    echo "⚠️  WARNING: GMAIL_APP_PASSWORD not set"
    echo ""
    echo "To enable email sending:"
    echo "  1. Go to: https://myaccount.google.com/apppasswords"
    echo "  2. Create app password for 'GoingMerry Screeners'"
    echo "  3. Run: export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'"
    echo "  4. Create secret:"
    echo "     echo -n 'your-app-password' | gcloud secrets create gmail-app-password --data-file=- --project=${PROJECT_ID}"
    echo ""
    echo "For now, running in preview mode (generates report but doesn't email)"
    echo ""
    USE_EMAIL=false
else
    echo "✓ GMAIL_APP_PASSWORD is set"
    USE_EMAIL=true

    # Create or update secret in Secret Manager
    echo "Storing Gmail App Password in Secret Manager..."

    # Check if secret exists
    if gcloud secrets describe gmail-app-password --project=${PROJECT_ID} &>/dev/null; then
        echo "  Updating existing secret..."
        echo -n "$GMAIL_APP_PASSWORD" | gcloud secrets versions add gmail-app-password \
            --data-file=- \
            --project=${PROJECT_ID}
    else
        echo "  Creating new secret..."
        echo -n "$GMAIL_APP_PASSWORD" | gcloud secrets create gmail-app-password \
            --data-file=- \
            --project=${PROJECT_ID}
    fi

    # Grant access to service account
    echo "  Granting access to prod-backend-sa..."
    gcloud secrets add-iam-policy-binding gmail-app-password \
        --project=${PROJECT_ID} \
        --member="serviceAccount:prod-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet 2>/dev/null || echo "    (Permission may already exist)"

    echo "✓ Gmail App Password stored securely"
fi

echo ""

# Create Cloud Run Job for daily summary report
echo "Creating Cloud Run Job for daily summary report..."

# Build command based on whether email is enabled
if [ "$USE_EMAIL" = true ]; then
    CMD_ARGS="python3,backend/jobs/daily_summary_report.py,--email,${EMAIL}"
    SET_SECRETS="GMAIL_APP_PASSWORD=gmail-app-password:latest"
else
    CMD_ARGS="python3,backend/jobs/daily_summary_report.py,--no-send"
    SET_SECRETS=""
fi

# Delete existing job if it exists
gcloud run jobs delete prod-daily-summary-report \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --quiet 2>/dev/null || echo "  (No existing job to delete)"

# Create new job
gcloud run jobs create prod-daily-summary-report \
    --image=us-east5-docker.pkg.dev/${PROJECT_ID}/prod-backend/api:latest \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --set-env-vars="GMAIL_SENDER=${GMAIL_SENDER}" \
    ${SET_SECRETS:+--set-secrets="$SET_SECRETS"} \
    --max-retries=2 \
    --task-timeout=10m \
    --memory=512Mi \
    --cpu=1 \
    --command=$(echo $CMD_ARGS | tr ',' '\n' | paste -sd, -) \
    --quiet

echo "✓ Cloud Run Job created: prod-daily-summary-report"
echo ""

# Create Cloud Scheduler job to run at 7 AM ET (12 PM UTC)
echo "Creating Cloud Scheduler to run daily at 7 AM ET..."

# Delete existing scheduler if it exists
gcloud scheduler jobs delete prod-daily-summary-scheduler \
    --location=${REGION} \
    --project=${PROJECT_ID} \
    --quiet 2>/dev/null || echo "  (No existing scheduler to delete)"

# Create scheduler
# 7 AM ET = 12 PM UTC (during standard time) or 11 AM UTC (during daylight time)
# Using America/New_York timezone handles DST automatically
gcloud scheduler jobs create http prod-daily-summary-scheduler \
    --location=${REGION} \
    --project=${PROJECT_ID} \
    --schedule="0 7 * * *" \
    --time-zone="America/New_York" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/prod-daily-summary-report:run" \
    --http-method=POST \
    --oauth-service-account-email=prod-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --quiet

echo "✓ Cloud Scheduler created: prod-daily-summary-scheduler"
echo "  Schedule: Daily at 7:00 AM ET"
echo ""

# Summary
echo "=========================================="
echo "✓ SETUP COMPLETE"
echo "=========================================="
echo ""
echo "What was created:"
echo "  • Cloud Run Job: prod-daily-summary-report"
echo "  • Cloud Scheduler: Daily at 7 AM ET"
if [ "$USE_EMAIL" = true ]; then
    echo "  • Email: Enabled → ${EMAIL}"
else
    echo "  • Email: Disabled (preview mode)"
fi
echo ""
echo "Next steps:"
echo "  1. Test the job manually:"
echo "     gcloud run jobs execute prod-daily-summary-report --region=${REGION}"
echo ""
echo "  2. View execution logs:"
echo "     gcloud run jobs logs read prod-daily-summary-report --region=${REGION} --limit=100"
echo ""
echo "  3. View scheduler status:"
echo "     gcloud scheduler jobs describe prod-daily-summary-scheduler --location=${REGION}"
echo ""
if [ "$USE_EMAIL" = false ]; then
    echo "  4. Enable email sending:"
    echo "     - Set GMAIL_APP_PASSWORD environment variable"
    echo "     - Re-run this script"
    echo ""
fi
echo "Report preview saved to: /tmp/screener_report_*.html"
echo ""
echo "Done!"
