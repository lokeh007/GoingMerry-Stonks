# Daily Stock Screeners - Cloud Run Job

Automated daily execution of The Undiscovered and The Coiled Spring screeners against the full NYSE + NASDAQ universe. Results are stored in Firestore for instant frontend loading.

## Overview

**Schedule:** 6:30 PM ET, Monday-Friday (after market close)
**Runtime:** 60-80 minutes for ~6000 stocks
**Cost:** ~$7-10/month
**Storage:** Firestore (12MB for 30-day retention)

## Architecture

```
Cloud Scheduler (6:30 PM ET Mon-Fri)
    ↓ Triggers
Cloud Run Job (serverless, 2 vCPU, 2GB RAM)
    ↓ Processes
6000 stocks from NYSE + NASDAQ
    ↓ Stores results in
Firestore (screeners/{name}/runs/{date})
    ↓ Frontend reads
Cached results (instant load, 0-24 hours old)
```

## Files

- **`run_daily_screeners.py`** - Main job script
- **`Dockerfile`** - Container image definition
- **`FIRESTORE_SCHEMA.md`** - Database schema documentation
- **`README.md`** - This file

## Prerequisites

1. **GCP Project** with billing enabled
2. **APIs enabled:**
   - Cloud Run
   - Cloud Scheduler
   - Firestore
   - Secret Manager
   - Artifact Registry
3. **Firestore database** created (Native mode)
4. **Polygon API key** stored in Secret Manager

## Local Testing

Test the job script locally before deploying:

```bash
cd backend

# Set environment variable
export POLYGON_API_KEY="your_api_key_here"

# Run the job (takes ~30 minutes for test universe)
python3 jobs/run_daily_screeners.py
```

**Expected output:**
```
================================================================================
DAILY STOCK SCREENERS - Starting execution
Timestamp: 2025-11-10T23:30:00.000000+00:00
================================================================================
Fetching full NYSE + NASDAQ universe...
Universe size: 500 stocks (MVP mode)
================================================================================
RUNNING: The Undiscovered Screener
================================================================================
Screening 500 stocks...
Parameters: inst_own<25.0%, analysts<=5, insider_buying=True
Progress: 50/500 stocks processed
Progress: 100/500 stocks processed
...
✓ Screening complete: 12 stocks passed
✗ Failed/skipped: 45 stocks
⏱  Execution time: 845.3 seconds
Saving undiscovered results to Firestore...
✓ Saved to Firestore: screeners/undiscovered/runs/2025-11-10
...
================================================================================
DAILY STOCK SCREENERS - Completed successfully
================================================================================
```

## Deployment

### Step 1: Build and Push Docker Image

```bash
cd backend

# Build image for daily screeners job
docker build -f jobs/Dockerfile -t us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest .

# Push to Artifact Registry
docker push us-east5-docker.pkg.dev/sylvan-earth-477020-u6/prod-backend/daily-screeners:latest
```

### Step 2: Deploy Infrastructure with Terraform

```bash
cd terraform/environments/prod

# Initialize terraform (first time only)
terraform init

# Preview changes
terraform plan

# Deploy Cloud Run Job + Cloud Scheduler
terraform apply

# Verify deployment
terraform output
```

**Expected terraform output:**
```
Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:

scheduled_jobs_job_name = "prod-daily-screeners"
scheduled_jobs_scheduler_name = "prod-trigger-daily-screeners"
scheduled_jobs_scheduler_schedule = "30 23 * * 1-5"
```

### Step 3: Verify Deployment

```bash
# Check Cloud Run Job
gcloud run jobs describe prod-daily-screeners --region=us-east5

# Check Cloud Scheduler
gcloud scheduler jobs describe prod-trigger-daily-screeners --location=us-east5

# Manual test run (doesn't wait for schedule)
gcloud run jobs execute prod-daily-screeners --region=us-east5 --wait

# View logs
gcloud run jobs logs read prod-daily-screeners --region=us-east5 --limit=100
```

## Monitoring

### View Job Executions

```bash
# Recent executions
gcloud run jobs executions list --job=prod-daily-screeners --region=us-east5

# Execution details
gcloud run jobs executions describe EXECUTION_ID --region=us-east5

# Logs for specific execution
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=prod-daily-screeners" --limit=100
```

### Check Firestore Data

```bash
# List screener runs
gcloud firestore indexes list

# Query latest run
firebase firestore:get screeners/undiscovered/runs/$(date +%Y-%m-%d)
```

### Key Metrics

Monitor these in Cloud Monitoring:

1. **Execution Time** - Should stay under 90 minutes
2. **Total Results** - Track if screeners find fewer stocks
3. **Failed Count** - High failure rate indicates API issues
4. **Memory Usage** - Should stay under 2GB
5. **Cost** - Should be ~$7-10/month

## Troubleshooting

### Job Fails to Start

**Error:** `Permission denied accessing secret`

**Solution:**
```bash
# Grant service account access to Polygon API key
gcloud secrets add-iam-policy-binding prod-polygon-api-key \
  --member="serviceAccount:prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Job Timeout

**Error:** `Execution exceeded timeout of 7200 seconds`

**Solution:** Increase timeout in terraform:
```hcl
job_timeout = 10800  # 3 hours
```

### Firestore Write Failures

**Error:** `Permission denied: Missing or insufficient permissions`

**Solution:**
```bash
# Grant Firestore access
gcloud projects add-iam-policy-binding sylvan-earth-477020-u6 \
  --member="serviceAccount:prod-backend-sa@sylvan-earth-477020-u6.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### High API Failure Rate

**Error:** `Failed to screen 200+ stocks`

**Symptoms:**
- Many stocks in `failed_tickers`
- Logs show yfinance errors

**Solution:**
1. Check Polygon API rate limits
2. Reduce universe size temporarily
3. Add retry logic with exponential backoff

## Scaling to Full NYSE/NASDAQ (6000+ stocks)

### Current MVP Limitations

The current implementation uses a **representative universe of ~500 stocks** for testing. To scale to the full NYSE/NASDAQ:

### Option 1: Third-Party API (Recommended)

Use a stock screener API that provides exchange listings:

```python
# Example: IEX Cloud
import requests

def get_full_exchange_universe() -> List[str]:
    """Fetch all NYSE + NASDAQ stocks with filters."""
    url = "https://cloud.iexapis.com/stable/ref-data/symbols"
    params = {
        "token": os.getenv("IEX_API_KEY"),
        "exchange": "nas,nys",  # NASDAQ + NYSE
    }
    response = requests.get(url, params=params)
    stocks = response.json()

    # Filter: Market cap >= $100M, Volume > 100K
    return [
        stock["symbol"]
        for stock in stocks
        if stock.get("marketCap", 0) >= 100_000_000
        and stock.get("avgVolume", 0) > 100_000
    ]
```

**Cost:** IEX Cloud free tier covers this (~5K stocks)

### Option 2: Pre-built CSV/JSON File

Maintain a curated list of tickers:

```python
def get_full_exchange_universe() -> List[str]:
    """Load pre-built universe from CSV."""
    with open("data/nyse_nasdaq_universe.csv") as f:
        reader = csv.reader(f)
        return [row[0] for row in reader if row[1] == "active"]
```

Download from:
- [NASDAQ FTP](ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt)
- [NYSE Listed](https://www.nyse.com/listings_directory/stock)

### Option 3: yfinance Bulk Download

```python
import yfinance as yf

def get_full_exchange_universe() -> List[str]:
    """Use yfinance to get major indices."""
    sp500 = yf.Ticker("^GSPC").info.get("components", [])
    nasdaq = yf.Ticker("^IXIC").info.get("components", [])
    return list(set(sp500 + nasdaq))
```

## Cost Optimization

### Reduce Execution Time

1. **Parallel processing:** Use asyncio for concurrent API calls
2. **Caching:** Cache fundamentals for 1 hour to avoid duplicate fetches
3. **Smaller universe:** Start with S&P 1500 instead of full 6000

### Reduce Frequency

- **Daily → 3x/week:** $7/month → $3/month
- **Only run on market open days** (exclude holidays)

### Optimize Resources

```hcl
# Lower memory for smaller universe
job_memory = "1Gi"  # Instead of 2Gi
job_cpu    = "1"    # Instead of 2
```

## Security

- ✅ Service account has minimal permissions (Firestore + Secret Manager)
- ✅ Secrets stored in Secret Manager (never in code)
- ✅ Firestore security rules allow public read, service account write only
- ✅ Job runs in isolated Cloud Run environment

## Future Enhancements

1. **Email alerts:** Notify when high-scoring stocks appear
2. **Change detection:** Highlight stocks new to the list
3. **Historical trends:** Track score changes over time
4. **Watchlists:** Let users save favorite stocks
5. **Export:** CSV/JSON download of results
6. **Smart Money real-time:** Hybrid approach with intraday refresh

## Support

**Documentation:**
- [Cloud Run Jobs](https://cloud.google.com/run/docs/create-jobs)
- [Cloud Scheduler](https://cloud.google.com/scheduler/docs)
- [Firestore](https://firebase.google.com/docs/firestore)

**Logs:**
- [Cloud Run Job Logs](https://console.cloud.google.com/run/jobs)
- [Cloud Scheduler Logs](https://console.cloud.google.com/cloudscheduler)

**Cost Analysis:**
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
