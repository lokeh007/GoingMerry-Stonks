#!/bin/bash
set -e

# Setup Comprehensive Monitoring for Batch Screener Jobs
#
# Creates:
# 1. Alerting policies for job failures
# 2. Log-based metrics for error tracking
# 3. Monitoring dashboard
# 4. Email notification channel
#
# Usage: ./scripts/setup-batch-monitoring.sh

PROJECT_ID="sylvan-earth-477020-u6"
REGION="us-east5"
EMAIL="brian.boatright@gmail.com"

echo "=========================================="
echo "Setting Up Batch Job Monitoring"
echo "=========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Email: ${EMAIL}"
echo ""

# Get notification channel ID (or create if doesn't exist)
echo "Step 1: Checking notification channel..."
CHANNEL_ID=$(gcloud alpha monitoring channels list \
  --project=${PROJECT_ID} \
  --filter="labels.email_address=${EMAIL}" \
  --format="value(name)" | head -1)

if [ -z "$CHANNEL_ID" ]; then
  echo "Creating email notification channel..."
  CHANNEL_ID=$(gcloud alpha monitoring channels create \
    --project=${PROJECT_ID} \
    --display-name="Email Notifications - Batch Jobs" \
    --type=email \
    --channel-labels=email_address=${EMAIL} \
    --format="value(name)")
fi

echo "✓ Notification channel: ${CHANNEL_ID}"
echo ""

# ============================================
# LAYER 1: Job Execution Failure Alarms
# ============================================
echo "Step 2: Creating job execution failure alarms..."

# Alarm 1: Regular Screeners Job Failures
cat > /tmp/alarm-regular-screeners-failure.yaml <<EOF
displayName: "Batch Jobs - Regular Screeners Failed"
documentation:
  content: "Regular screener batch jobs (Undiscovered + Coiled Spring) failed to complete successfully"
  mimeType: "text/markdown"
conditions:
  - displayName: "Job execution failed"
    conditionThreshold:
      filter: |
        resource.type="cloud_run_job"
        resource.labels.job_name=monitoring.regex().full_match("prod-regular-screeners-batch-.*")
        metric.type="run.googleapis.com/job/completed_execution_count"
        metric.labels.result="failed"
      comparison: COMPARISON_GT
      thresholdValue: 0
      duration: 60s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
notificationChannels:
  - ${CHANNEL_ID}
alertStrategy:
  autoClose: 3600s
enabled: true
EOF

gcloud alpha monitoring policies create --policy-from-file=/tmp/alarm-regular-screeners-failure.yaml --project=${PROJECT_ID} 2>/dev/null || \
  echo "  (Alarm may already exist - skipping)"

# Alarm 2: Smart Money Screeners Job Failures
cat > /tmp/alarm-smart-money-failure.yaml <<EOF
displayName: "Batch Jobs - Smart Money Screeners Failed"
documentation:
  content: "Smart Money screener batch jobs (Options Flow) failed to complete successfully"
  mimeType: "text/markdown"
conditions:
  - displayName: "Job execution failed"
    conditionThreshold:
      filter: |
        resource.type="cloud_run_job"
        resource.labels.job_name=monitoring.regex().full_match("prod-smart-money-screeners-batch-.*")
        metric.type="run.googleapis.com/job/completed_execution_count"
        metric.labels.result="failed"
      comparison: COMPARISON_GT
      thresholdValue: 0
      duration: 60s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
notificationChannels:
  - ${CHANNEL_ID}
alertStrategy:
  autoClose: 3600s
enabled: true
EOF

gcloud alpha monitoring policies create --policy-from-file=/tmp/alarm-smart-money-failure.yaml --project=${PROJECT_ID} 2>/dev/null || \
  echo "  (Alarm may already exist - skipping)"

echo "✓ Job failure alarms created"
echo ""

# ============================================
# LAYER 2: Log-based Metrics for Error Tracking
# ============================================
echo "Step 3: Creating log-based metrics..."

# Metric 1: Data Errors (404, no_data)
gcloud logging metrics create screener_data_errors \
  --project=${PROJECT_ID} \
  --description="Count of data errors (404, no data, delisted tickers)" \
  --log-filter='
    resource.type="cloud_run_job"
    resource.labels.job_name=~"prod-.*-screeners-batch-.*"
    (
      jsonPayload.message=~".*404.*" OR
      jsonPayload.message=~".*no data.*" OR
      jsonPayload.message=~".*not found.*" OR
      jsonPayload.message=~".*DELISTED.*"
    )
    severity>=WARNING
  ' \
  --value-extractor='EXTRACT(1)' 2>/dev/null || echo "  (Metric may already exist - skipping)"

# Metric 2: Rate Limit Errors
gcloud logging metrics create screener_rate_limit_errors \
  --project=${PROJECT_ID} \
  --description="Count of rate limit errors from yfinance" \
  --log-filter='
    resource.type="cloud_run_job"
    resource.labels.job_name=~"prod-.*-screeners-batch-.*"
    (
      jsonPayload.message=~".*rate limit.*" OR
      jsonPayload.message=~".*too many requests.*" OR
      jsonPayload.message=~".*429.*"
    )
    severity>=WARNING
  ' \
  --value-extractor='EXTRACT(1)' 2>/dev/null || echo "  (Metric may already exist - skipping)"

# Metric 3: Stocks Discovered (Undiscovered)
gcloud logging metrics create screener_undiscovered_count \
  --project=${PROJECT_ID} \
  --description="Number of stocks found by Undiscovered screener" \
  --log-filter='
    resource.type="cloud_run_job"
    resource.labels.job_name=~"prod-regular-screeners-batch-.*"
    jsonPayload.message=~".*Undiscovered:.*stocks passed.*"
  ' \
  --value-extractor='REGEXP_EXTRACT(jsonPayload.message, "Undiscovered: (\\d+)")' 2>/dev/null || echo "  (Metric may already exist - skipping)"

# Metric 4: Stocks Discovered (Coiled Spring)
gcloud logging metrics create screener_coiled_spring_count \
  --project=${PROJECT_ID} \
  --description="Number of stocks found by Coiled Spring screener" \
  --log-filter='
    resource.type="cloud_run_job"
    resource.labels.job_name=~"prod-regular-screeners-batch-.*"
    jsonPayload.message=~".*Coiled Spring:.*stocks passed.*"
  ' \
  --value-extractor='REGEXP_EXTRACT(jsonPayload.message, "Coiled Spring: (\\d+)")' 2>/dev/null || echo "  (Metric may already exist - skipping)"

# Metric 5: Stocks Discovered (Smart Money)
gcloud logging metrics create screener_smart_money_count \
  --project=${PROJECT_ID} \
  --description="Number of stocks found by Smart Money screener" \
  --log-filter='
    resource.type="cloud_run_job"
    resource.labels.job_name=~"prod-smart-money-screeners-batch-.*"
    jsonPayload.message=~".*Screening complete:.*stocks passed.*"
  ' \
  --value-extractor='REGEXP_EXTRACT(jsonPayload.message, "complete: (\\d+)")' 2>/dev/null || echo "  (Metric may already exist - skipping)"

echo "✓ Log-based metrics created"
echo ""

# ============================================
# LAYER 3: High Error Rate Alarm
# ============================================
echo "Step 4: Creating error rate alarms..."

# Alarm for high data error rate
cat > /tmp/alarm-high-data-errors.yaml <<EOF
displayName: "Batch Jobs - High Data Error Rate"
documentation:
  content: "Screener jobs are experiencing high rate of data errors (404, no data). May indicate issues with ticker universe or yfinance API."
  mimeType: "text/markdown"
conditions:
  - displayName: "Data errors > 50 per hour"
    conditionThreshold:
      filter: |
        resource.type="cloud_run_job"
        metric.type="logging.googleapis.com/user/screener_data_errors"
      comparison: COMPARISON_GT
      thresholdValue: 50
      duration: 3600s
      aggregations:
        - alignmentPeriod: 3600s
          perSeriesAligner: ALIGN_SUM
notificationChannels:
  - ${CHANNEL_ID}
alertStrategy:
  autoClose: 7200s
enabled: true
EOF

gcloud alpha monitoring policies create --policy-from-file=/tmp/alarm-high-data-errors.yaml --project=${PROJECT_ID} 2>/dev/null || \
  echo "  (Alarm may already exist - skipping)"

# Alarm for rate limiting issues
cat > /tmp/alarm-rate-limiting.yaml <<EOF
displayName: "Batch Jobs - Rate Limiting Issues"
documentation:
  content: "Screener jobs are hitting rate limits. May need to reduce rate or increase backoff."
  mimeType: "text/markdown"
conditions:
  - displayName: "Rate limit errors > 10 per hour"
    conditionThreshold:
      filter: |
        resource.type="cloud_run_job"
        metric.type="logging.googleapis.com/user/screener_rate_limit_errors"
      comparison: COMPARISON_GT
      thresholdValue: 10
      duration: 3600s
      aggregations:
        - alignmentPeriod: 3600s
          perSeriesAligner: ALIGN_SUM
notificationChannels:
  - ${CHANNEL_ID}
alertStrategy:
  autoClose: 7200s
enabled: true
EOF

gcloud alpha monitoring policies create --policy-from-file=/tmp/alarm-rate-limiting.yaml --project=${PROJECT_ID} 2>/dev/null || \
  echo "  (Alarm may already exist - skipping)"

echo "✓ Error rate alarms created"
echo ""

# ============================================
# Summary
# ============================================
echo "=========================================="
echo "✓ MONITORING SETUP COMPLETE"
echo "=========================================="
echo ""
echo "Created:"
echo "  - 4 alerting policies"
echo "  - 5 log-based metrics"
echo "  - Email notifications to: ${EMAIL}"
echo ""
echo "Next Steps:"
echo "  1. View alarms: https://console.cloud.google.com/monitoring/alerting?project=${PROJECT_ID}"
echo "  2. View metrics: https://console.cloud.google.com/logs/metrics?project=${PROJECT_ID}"
echo "  3. Setup daily summary report (see scripts/create-daily-summary-report.py)"
echo ""
echo "Clean up temp files..."
rm -f /tmp/alarm-*.yaml

echo "Done!"
