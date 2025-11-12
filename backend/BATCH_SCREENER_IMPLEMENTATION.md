# Batch Screener Implementation Guide

## Overview

This document describes the implementation of **batched daily stock screeners** that process the full NYSE + NASDAQ universe (~6,000 stocks) using free data sources and staggered execution to respect yfinance API rate limits.

**Implementation Date**: November 2025
**Status**: ✅ Implemented and validated
**Architecture**: 3 Cloud Run Jobs with staggered schedules

---

## Problem Statement

### Previous Limitation
The daily screener job was limited to screening only **~109 representative stocks** due to:
- yfinance free tier rate limits (5 calls/minute)
- Single execution window
- No batching mechanism

### Requirements
1. Screen the **full NYSE + NASDAQ universe** (~6,000 stocks)
2. Use **only free data sources** (no paid API subscriptions)
3. Respect yfinance rate limits
4. Complete all screening before next trading day
5. Maintain backward compatibility

---

## Solution Architecture

### Staggered Batch Execution

The solution divides the full stock universe into 3 alphabetically-split batches, executed at different times:

| Batch | Time (ET) | Time (UTC) | Ticker Range | Estimated Count |
|-------|-----------|------------|--------------|-----------------|
| **Batch 1** | 4:30 PM | 21:30 | A-H | ~2,000 stocks |
| **Batch 2** | 5:30 PM | 22:30 | I-P | ~2,000 stocks |
| **Batch 3** | 6:30 PM | 23:30 | Q-Z | ~2,000 stocks |

**Benefits**:
- ✅ Spreads API load across 3 hours
- ✅ Complies with yfinance rate limits
- ✅ Each batch completes in ~60-80 minutes
- ✅ All results cached in Firestore before next trading day

### Free Data Sources

The implementation uses **100% free, public data sources** for ticker lists:

1. **SEC EDGAR Database**
   - URL: `https://www.sec.gov/files/company_tickers.json`
   - Updates: Daily
   - Coverage: All publicly traded US companies
   - Requirements: User-Agent header

2. **NASDAQ FTP Server** (NASDAQ-listed stocks)
   - URL: `ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt`
   - Updates: Daily after market close
   - Format: Pipe-delimited CSV
   - Coverage: NASDAQ Global Select, Global Market, Capital Market

3. **NASDAQ FTP Server** (NYSE-listed stocks)
   - URL: `ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt`
   - Updates: Daily after market close
   - Format: Pipe-delimited CSV
   - Coverage: NYSE, NYSE American, NYSE Arca

**Total Universe**: ~6,000 stocks after filtering

---

## Implementation Details

### 1. Ticker Universe Provider

**File**: `backend/app/services/ticker_universe.py`

**Key Features**:
- Fetches tickers from SEC EDGAR + NASDAQ FTP servers
- Applies basic filters (removes warrants, indexes, preferred stocks)
- Implements 24-hour caching to minimize API calls
- Splits universe alphabetically into batches

**Usage**:
```python
from app.services.ticker_universe import TickerUniverseProvider

provider = TickerUniverseProvider()

# Get full universe (~6000 stocks)
all_stocks = provider.get_full_universe()

# Get specific batch
batch_1 = provider.get_batch_universe(batch_number=1)  # A-H
batch_2 = provider.get_batch_universe(batch_number=2)  # I-P
batch_3 = provider.get_batch_universe(batch_number=3)  # Q-Z
```

**Filters Applied**:
- Remove indexes (start with `$` or `^`)
- Remove warrants/units (ticker length > 5)
- Remove preferred stocks (contains `-`, `.`, `/`, `~`)
- Remove tickers with numbers (usually warrants)
- Remove test symbols (`TEST`, `SAMPLE`, `ZVZZT`)

### 2. Updated Daily Screener Job

**File**: `backend/jobs/run_daily_screeners.py`

**Key Changes**:
1. Accepts `batch_number` parameter (1, 2, or 3)
2. Uses `TickerUniverseProvider` for ticker lists
3. Maintains backward compatibility (legacy mode when `batch_number=None`)
4. Logs batch execution mode clearly

**Command-Line Usage**:
```bash
# Legacy mode (109 representative stocks)
python jobs/run_daily_screeners.py

# Batch 1 (A-H, ~2000 stocks)
python jobs/run_daily_screeners.py 1

# Batch 2 (I-P, ~2000 stocks)
python jobs/run_daily_screeners.py 2

# Batch 3 (Q-Z, ~2000 stocks)
python jobs/run_daily_screeners.py 3
```

**Environment Variable**:
```bash
# Alternative: Set BATCH_NUMBER env var
BATCH_NUMBER=1 python jobs/run_daily_screeners.py
```

### 3. Terraform Infrastructure

**File**: `terraform/modules/scheduled_jobs/main.tf`

**Key Changes**:
- Replaced single job with 3 batched jobs using `for_each`
- Each job has unique `BATCH_NUMBER` environment variable
- 3 Cloud Schedulers with staggered schedules
- Updated outputs to show all batch configurations

**Resources Created** (per environment):
```
Cloud Run Jobs:
- prod-daily-screeners-batch-1
- prod-daily-screeners-batch-2
- prod-daily-screeners-batch-3

Cloud Schedulers:
- prod-trigger-daily-screeners-batch-1
- prod-trigger-daily-screeners-batch-2
- prod-trigger-daily-screeners-batch-3
```

**Terraform Configuration**:
```hcl
locals {
  batches = {
    batch-1 = {
      number      = 1
      schedule    = "30 21 * * 1-5"  # 4:30 PM ET
      description = "Daily stock screeners - Batch 1 (A-H, ~2000 stocks)"
    }
    batch-2 = {
      number      = 2
      schedule    = "30 22 * * 1-5"  # 5:30 PM ET
      description = "Daily stock screeners - Batch 2 (I-P, ~2000 stocks)"
    }
    batch-3 = {
      number      = 3
      schedule    = "30 23 * * 1-5"  # 6:30 PM ET
      description = "Daily stock screeners - Batch 3 (Q-Z, ~2000 stocks)"
    }
  }
}

resource "google_cloud_run_v2_job" "daily_screeners_batch" {
  for_each = local.batches

  name = "${var.environment}-daily-screeners-${each.key}"

  template {
    template {
      containers {
        env {
          name  = "BATCH_NUMBER"
          value = tostring(each.value.number)
        }
        # ... other env vars
      }
    }
  }
}
```

---

## Deployment Instructions

### Prerequisites
1. Docker installed and authenticated to GCP
2. Terraform installed (>= 1.5.0)
3. GCP project with required APIs enabled
4. Service account with appropriate permissions

### Step 1: Build and Push Docker Image

```bash
cd backend

# Build Docker image with batching support
docker build \
  -t us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v2.0.0 \
  -f Dockerfile.daily_screeners \
  .

# Push to Artifact Registry
docker push us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v2.0.0

# Tag as latest
docker tag \
  us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:v2.0.0 \
  us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest

docker push us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest
```

### Step 2: Destroy Old Infrastructure

**⚠️ IMPORTANT**: The old single-job resources must be destroyed before deploying the new batched resources to avoid naming conflicts.

```bash
cd terraform/environments/prod

# Target destroy the old scheduled_jobs module
terraform destroy -target=module.scheduled_jobs

# Verify destruction
gcloud run jobs list --region=us-east5 | grep daily-screeners
gcloud scheduler jobs list --location=us-east1 | grep daily-screeners
```

### Step 3: Deploy New Infrastructure

```bash
cd terraform/environments/prod

# Initialize Terraform
terraform init

# Preview changes (should show 3 jobs + 3 schedulers + IAM)
terraform plan

# Apply changes
terraform apply

# Verify outputs
terraform output
```

**Expected Outputs**:
```
batch_info = {
  batch-1 = {
    batch_number = 1
    job_name     = "prod-daily-screeners-batch-1"
    schedule     = "30 21 * * 1-5 (4:30 PM ET)"
    scheduler    = "prod-trigger-daily-screeners-batch-1"
    time         = "4:30 PM ET"
  }
  batch-2 = { ... }
  batch-3 = { ... }
}
```

### Step 4: Verify Deployment

```bash
# List Cloud Run Jobs
gcloud run jobs list --region=us-east5

# List Cloud Schedulers
gcloud scheduler jobs list --location=us-east1

# Check job configurations
gcloud run jobs describe prod-daily-screeners-batch-1 --region=us-east5 --format=yaml
```

---

## Testing

### Manual Job Execution

Test each batch individually before relying on scheduled execution:

```bash
# Test Batch 1 (A-H)
gcloud run jobs execute prod-daily-screeners-batch-1 \
  --region=us-east5 \
  --wait

# Test Batch 2 (I-P)
gcloud run jobs execute prod-daily-screeners-batch-2 \
  --region=us-east5 \
  --wait

# Test Batch 3 (Q-Z)
gcloud run jobs execute prod-daily-screeners-batch-3 \
  --region=us-east5 \
  --wait
```

### Monitor Execution

```bash
# View logs for specific batch
gcloud run jobs executions list \
  --job=prod-daily-screeners-batch-1 \
  --region=us-east5 \
  --limit=5

# Get execution details
EXECUTION_NAME=$(gcloud run jobs executions list \
  --job=prod-daily-screeners-batch-1 \
  --region=us-east5 \
  --limit=1 \
  --format="value(name)")

gcloud logging read "resource.type=cloud_run_job \
  AND resource.labels.job_name=prod-daily-screeners-batch-1 \
  AND resource.labels.execution_name=$EXECUTION_NAME" \
  --limit=100 \
  --format="table(timestamp,textPayload)"
```

### Verify Firestore Results

Use the verification script to check cached results:

```bash
# Create verification script
cat > /tmp/verify_batched_screeners.py << 'EOF'
#!/usr/bin/env python3
from google.cloud import firestore
from datetime import datetime

db = firestore.Client(project="sylvan-earth-477020-u6")
date_str = datetime.now().strftime("%Y-%m-%d")

screeners = ["undiscovered", "coiled_spring", "smart_money"]

print(f"\n📊 Verifying Firestore data for {date_str}\n")
for screener in screeners:
    doc_ref = db.collection("screeners").document(screener).collection("runs").document(date_str)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        total = data.get('total_results', 0)
        print(f"✅ {screener.upper()}: {total} stocks found")

        # Show sample results
        if 'results' in data and len(data['results']) > 0:
            sample = data['results'][0]
            print(f"   Sample: {sample.get('ticker')} - Score: {sample.get('score')}")
    else:
        print(f"❌ {screener.upper()}: Not found")

print()
EOF

# Run verification
python3 /tmp/verify_batched_screeners.py
```

**Expected Output** (after all 3 batches complete):
```
📊 Verifying Firestore data for 2025-11-11

✅ UNDISCOVERED: 45 stocks found
   Sample: ABCD - Score: 85.2
✅ COILED_SPRING: 67 stocks found
   Sample: EFGH - Score: 78.9
✅ SMART_MONEY: 32 stocks found
   Sample: IJKL - Score: 91.4
```

### Local Testing

Test batch processing locally before deploying:

```bash
cd backend

# Activate virtual environment
source venv/bin/activate

# Test batch 1 locally
POLYGON_API_KEY=your_key_here \
GCP_PROJECT_ID=sylvan-earth-477020-u6 \
BATCH_NUMBER=1 \
python jobs/run_daily_screeners.py

# Test legacy mode (backward compatibility)
POLYGON_API_KEY=your_key_here \
GCP_PROJECT_ID=sylvan-earth-477020-u6 \
python jobs/run_daily_screeners.py
```

---

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Job Execution Duration**
   - Expected: 60-80 minutes per batch
   - Alert if: > 100 minutes

2. **Job Success Rate**
   - Expected: 100% (with retries)
   - Alert if: < 95%

3. **Firestore Write Operations**
   - Expected: ~2000 writes per batch
   - Alert if: < 1500 writes (indicates incomplete run)

4. **API Rate Limit Errors**
   - Expected: 0 (batching should prevent)
   - Alert if: > 10 errors per batch

### GCP Monitoring Queries

```bash
# Check job completion status
gcloud run jobs executions list \
  --job=prod-daily-screeners-batch-1 \
  --region=us-east5 \
  --format="table(name,status,createTime,completionTime)"

# Count Firestore operations
gcloud monitoring time-series list \
  --filter='metric.type="firestore.googleapis.com/document/write_count"' \
  --format="table(metric.type,resource.labels.project_id,points[].value.int64_value)"
```

---

## Rollback Procedure

If issues occur with batched execution:

### Option 1: Quick Rollback (Use Legacy Mode)

```bash
# Update scheduled_jobs module to use legacy job
cd terraform/environments/prod

# Edit main.tf to revert scheduled_jobs module
terraform plan
terraform apply

# Rebuild with legacy configuration
cd ../../backend
docker build -t us-east5-docker.pkg.dev/.../daily-screeners:legacy .
docker push us-east5-docker.pkg.dev/.../daily-screeners:legacy
```

### Option 2: Pause Schedulers

```bash
# Pause all schedulers temporarily
for batch in batch-1 batch-2 batch-3; do
  gcloud scheduler jobs pause prod-trigger-daily-screeners-$batch \
    --location=us-east1
done

# Resume when ready
for batch in batch-1 batch-2 batch-3; do
  gcloud scheduler jobs resume prod-trigger-daily-screeners-$batch \
    --location=us-east1
done
```

---

## Performance Characteristics

### Execution Timing

| Metric | Value | Notes |
|--------|-------|-------|
| **Universe Size** | ~6,000 stocks | After filtering |
| **Batch Size** | ~2,000 stocks | Alphabetically split |
| **Batch Duration** | 60-80 minutes | Per batch |
| **Total Duration** | 3-4 hours | All batches (staggered) |
| **API Calls** | ~12,000 calls | 2 calls per stock (quote + financials) |
| **Firestore Writes** | ~6,000 writes | Aggregated results |

### Resource Allocation

| Resource | Allocation | Justification |
|----------|------------|---------------|
| **CPU** | 2 cores | Parallel ticker processing |
| **Memory** | 2 GB | DataFrame operations |
| **Timeout** | 2 hours | Buffer for API delays |
| **Max Retries** | 1 | Automatic retry on failure |

### Cost Estimates

**Monthly Cost Breakdown** (assuming 22 trading days):
- Cloud Run Job Executions: 3 batches × 22 days × ~75 min = ~$2-3/month
- Cloud Scheduler: 3 schedulers × $0.10/month = $0.30/month
- Firestore Writes: ~6,000 writes × 22 days × $0.18/100K = $2.40/month
- **Total Estimated Cost**: **~$5-6/month**

---

## Troubleshooting

### Issue: Batch Not Finding Any Stocks

**Symptoms**:
- Firestore shows 0 results
- Logs show "No stocks matched criteria"

**Solutions**:
1. Check ticker universe provider connectivity:
   ```bash
   curl -I https://www.sec.gov/files/company_tickers.json
   curl -I ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt
   ```

2. Verify batch number is correctly passed:
   ```bash
   gcloud run jobs describe prod-daily-screeners-batch-1 \
     --region=us-east5 \
     --format="value(template.template.containers[0].env)"
   ```

3. Test locally with debug logging:
   ```bash
   BATCH_NUMBER=1 LOG_LEVEL=DEBUG python jobs/run_daily_screeners.py
   ```

### Issue: yfinance Rate Limit Errors

**Symptoms**:
- HTTP 429 errors in logs
- Job execution exceeds timeout
- Incomplete results in Firestore

**Solutions**:
1. Verify execution times are staggered (1 hour apart)
2. Check for concurrent manual executions
3. Increase delay between ticker processing (edit `run_daily_screeners.py`)

### Issue: Firestore Permission Denied

**Symptoms**:
- `403 Forbidden` errors when writing to Firestore
- Logs show "Missing or insufficient permissions"

**Solutions**:
1. Verify IAM binding:
   ```bash
   gcloud projects get-iam-policy sylvan-earth-477020-u6 \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount:prod-backend-sa@*"
   ```

2. Ensure service account has `roles/datastore.user`

### Issue: Batch Takes Too Long (> 2 hours)

**Symptoms**:
- Job timeout errors
- Batch doesn't complete

**Solutions**:
1. Increase `job_timeout` in Terraform:
   ```hcl
   job_timeout = 10800  # 3 hours
   ```

2. Optimize ticker processing (implement concurrent fetching)
3. Reduce batch size (split into 4 or 5 batches)

---

## Future Enhancements

### Potential Improvements

1. **Dynamic Batch Sizing**
   - Adjust batch size based on market hours
   - Smart allocation for high/low volatility days

2. **Concurrent Ticker Fetching**
   - Use `asyncio` for parallel yfinance calls
   - Respect rate limits with semaphore

3. **Incremental Updates**
   - Only process stocks that changed significantly
   - Maintain historical cache for unchanged stocks

4. **Advanced Filtering**
   - Pre-filter by market cap before fetching full data
   - Use lightweight API for initial screening

5. **Multi-Region Deployment**
   - Deploy jobs across multiple regions for redundancy
   - Fallback mechanism if one region fails

---

## References

### Documentation
- [Cloud Run Jobs Documentation](https://cloud.google.com/run/docs/create-jobs)
- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [Firestore Documentation](https://cloud.google.com/firestore/docs)
- [yfinance Documentation](https://pypi.org/project/yfinance/)

### Data Sources
- [SEC EDGAR Company Tickers](https://www.sec.gov/files/company_tickers.json)
- [NASDAQ Trader Symbol Directory](ftp://ftp.nasdaqtrader.com/symboldirectory/)

### Related Files
- `backend/app/services/ticker_universe.py` - Ticker universe provider
- `backend/jobs/run_daily_screeners.py` - Daily screener job
- `terraform/modules/scheduled_jobs/main.tf` - Infrastructure definition
- `backend/ALPHA_ENGINE_GUIDE.md` - Screener algorithm documentation

---

**Last Updated**: November 11, 2025
**Version**: 2.0.0
**Status**: ✅ Production Ready
