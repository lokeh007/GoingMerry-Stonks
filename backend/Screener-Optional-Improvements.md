# Stock Screener Optional Improvements

**Purpose**: This document outlines potential enhancements to improve screener performance, user experience, and result quality.

**Last Updated**: 2025-11-10
**Status**: Reference document for future development

---

## 🎯 Quick Wins (Easy & High Impact)

### 1. Add Progress Indicators
**Problem**: Users wait 30-40 seconds with no feedback
**Solution**: Stream progress updates to frontend

**Backend Implementation**:
```python
# Option A: Add progress field to response (simple)
@router.get("/smart-money")
async def get_smart_money(...):
    for i, ticker in enumerate(stock_universe):
        # ... process ticker ...
        if i % 5 == 0:  # Log every 5 stocks
            logger.info(f"Progress: {i+1}/{len(stock_universe)} stocks processed")

# Option B: Use Server-Sent Events (SSE) for real-time updates
from sse_starlette.sse import EventSourceResponse

@router.get("/smart-money/stream")
async def stream_smart_money(...):
    async def event_generator():
        for i, ticker in enumerate(stock_universe):
            result = process_stock(ticker)
            yield {
                "event": "progress",
                "data": json.dumps({
                    "current": i + 1,
                    "total": len(stock_universe),
                    "ticker": ticker,
                    "status": "processing"
                })
            }
        yield {"event": "complete", "data": json.dumps(results)}

    return EventSourceResponse(event_generator())
```

**Frontend Implementation**:
```typescript
// Show progress bar in UI
const [progress, setProgress] = useState({ current: 0, total: 0 });

// Option A: Poll progress endpoint
const checkProgress = setInterval(() => {
  // Update progress from backend logs
}, 1000);

// Option B: Use EventSource for SSE
const eventSource = new EventSource('/api/screener/smart-money/stream');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  setProgress(data);
};
```

**Impact**: ⭐⭐⭐⭐⭐
**Effort**: 2-4 hours
**Priority**: HIGH

---

### 2. Reduce Default Universe Size
**Problem**: 46 stocks take 37 seconds to screen
**Solution**: Use smaller default universe or add "quick" option

**Implementation**:
```python
# Option A: Change default to "tech" (31 stocks, 25 seconds)
@router.get("/smart-money")
async def get_smart_money(
    universe: StockUniverse = Query(
        StockUniverse.TECH,  # Changed from POPULAR
        description="Stock universe to screen",
    ),
):

# Option B: Add "quick" universe (15-20 top stocks)
universes = {
    "quick": [
        # Mega-cap stocks most likely to have active options
        "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD",
        "COIN", "PLTR", "SNOW", "UBER", "SHOP", "SQ", "ZM",
    ],
    "popular": [...],  # Keep existing
    ...
}

# Option C: Add page size/limit parameter
@router.get("/smart-money")
async def get_smart_money(
    universe: str = "popular",
    limit: int = Query(20, ge=10, le=100, description="Max stocks to screen"),
):
    stock_universe = yf_provider.get_stock_universe(universe)[:limit]
```

**Recommended**: Option C (add limit parameter) - most flexible

**Impact**: ⭐⭐⭐⭐⭐
**Effort**: 30 minutes
**Priority**: HIGH

---

### 3. Relax Default Filter Thresholds
**Problem**: Strict criteria return 0 results
**Solution**: Provide "aggressive" and "moderate" presets

**Implementation**:
```python
# Add preset parameter
@router.get("/smart-money")
async def get_smart_money(
    preset: str = Query("moderate", regex="^(aggressive|moderate|strict)$"),
    # Override with custom values if provided
    min_call_to_put_ratio: Optional[float] = None,
    unusual_volume_multiplier: Optional[float] = None,
):
    # Define presets
    presets = {
        "aggressive": {
            "min_call_to_put_ratio": 1.5,  # More permissive
            "unusual_volume_multiplier": 1.5,
        },
        "moderate": {
            "min_call_to_put_ratio": 2.0,  # Balanced
            "unusual_volume_multiplier": 1.75,
        },
        "strict": {
            "min_call_to_put_ratio": 3.0,  # Current default
            "unusual_volume_multiplier": 2.0,
        },
    }

    # Use preset values, allow overrides
    preset_values = presets[preset]
    final_call_put = min_call_to_put_ratio or preset_values["min_call_to_put_ratio"]
    final_volume = unusual_volume_multiplier or preset_values["unusual_volume_multiplier"]
```

**Frontend Update**:
```typescript
// Add preset selector to UI
<select onChange={(e) => setPreset(e.target.value)}>
  <option value="aggressive">More Results (Aggressive)</option>
  <option value="moderate">Balanced (Moderate)</option>
  <option value="strict">High Quality (Strict)</option>
</select>
```

**Impact**: ⭐⭐⭐⭐⭐
**Effort**: 1-2 hours
**Priority**: HIGH

---

### 4. Add Data Caching
**Problem**: Fetching same stock data repeatedly is slow
**Solution**: Cache fundamentals, options, and institutional data

**Implementation**:
```python
# Already partially implemented in yfinance_provider.py
# Expand caching strategy

import redis
from datetime import timedelta

class CachedYFinanceProvider(YFinanceProvider):
    def __init__(self):
        super().__init__()
        # Option A: Use Redis for distributed caching
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=6379,
            decode_responses=True
        )

        # Option B: Use in-memory cache (simpler, already implemented)
        # self.cache is already defined in YFinanceProvider

    def get_fundamentals(self, ticker: str) -> dict:
        cache_key = f"fundamentals:{ticker}"

        # Check Redis cache
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        # Fetch from API
        data = super().get_fundamentals(ticker)

        # Cache for 1 hour (fundamentals don't change frequently)
        self.redis_client.setex(
            cache_key,
            timedelta(hours=1),
            json.dumps(data)
        )

        return data

    def get_options_flow_metrics(self, ticker: str) -> dict:
        cache_key = f"options_flow:{ticker}"

        # Check cache
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        # Fetch from API
        data = super().get_options_flow_metrics(ticker)

        # Cache for 15 minutes (options volume changes frequently)
        self.redis_client.setex(
            cache_key,
            timedelta(minutes=15),
            json.dumps(data)
        )

        return data
```

**Cache TTL Strategy**:
- **Fundamentals**: 1 hour (PE, PEG, debt ratios change slowly)
- **Options flow**: 15 minutes (volume changes intraday)
- **Analyst/Insider data**: 6 hours (updated weekly/monthly)
- **Price data**: 5 minutes (for real-time quotes)

**Impact**: ⭐⭐⭐⭐ (Second run: 2-3 seconds!)
**Effort**: 3-4 hours (Redis setup + integration)
**Priority**: MEDIUM (high impact but requires infrastructure)

---

### 5. Parallelize API Calls (with Rate Limiting)
**Problem**: Serial processing takes 0.8s per stock
**Solution**: Process multiple stocks concurrently

**Implementation**:
```python
import asyncio
from asyncio import Semaphore

class AsyncYFinanceProvider:
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = Semaphore(max_concurrent)
        self.rate_limiter = asyncio.Semaphore(10)  # Max 10 calls/sec

    async def get_fundamentals_async(self, ticker: str) -> dict:
        async with self.semaphore:  # Limit concurrency
            async with self.rate_limiter:  # Rate limit
                await asyncio.sleep(0.2)  # Respect yfinance limits
                # Use asyncio-compatible yfinance wrapper or run_in_executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    self.get_fundamentals,
                    ticker
                )

    async def screen_stocks_async(self, tickers: List[str]) -> List[dict]:
        # Process multiple stocks concurrently
        tasks = [self.get_fundamentals_async(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if not isinstance(r, Exception)]

# In router endpoint
@router.get("/smart-money")
async def get_smart_money(...):
    yf_provider = AsyncYFinanceProvider(max_concurrent=5)

    # Process 5 stocks at a time
    results = await yf_provider.screen_stocks_async(stock_universe)

    # ... continue with filtering logic ...
```

**Performance Gain**:
- **Current**: 46 stocks × 0.8s = 37 seconds
- **With 5 concurrent**: 46 stocks ÷ 5 × 0.8s = **7.4 seconds** (80% faster!)

**Impact**: ⭐⭐⭐⭐⭐
**Effort**: 4-6 hours (async refactor)
**Priority**: MEDIUM-HIGH

---

## 📊 Data Quality Improvements

### 6. Improve Options Volume Baseline
**Problem**: Current implementation estimates 30-day average as `current_volume * 0.7`
**Solution**: Calculate actual historical average

**Implementation**:
```python
def get_options_flow_metrics(self, ticker: str) -> dict:
    # Current: Estimates average from current volume
    avg_30day_volume = total_option_volume * 0.7  # ❌ Inaccurate

    # Better: Store historical volumes and calculate real average
    # Option A: Use database to track historical volumes
    historical_volumes = db.query(
        "SELECT AVG(total_volume) FROM option_volumes "
        "WHERE ticker = %s AND date >= NOW() - INTERVAL '30 days'",
        ticker
    )
    avg_30day_volume = historical_volumes[0] if historical_volumes else None

    # Option B: Fetch from premium data provider
    # (yfinance free tier doesn't have historical option volume)
```

**Alternative**: Accept current limitation and document it clearly

**Impact**: ⭐⭐⭐ (More accurate unusual volume detection)
**Effort**: 4-8 hours (requires database or premium data)
**Priority**: LOW (current estimation is "good enough" for screening)

---

### 7. Add Sweep Detection (Premium Data Required)
**Problem**: Free yfinance doesn't provide sweep/aggressive order data
**Solution**: Integrate premium options data provider

**Premium Data Providers**:
- **Unusual Whales** ($49/month) - Best for retail traders
- **FlowAlgo** ($89/month) - Real-time options flow
- **Market Chameleon** ($79/month) - Historical + real-time
- **Cboe DataShop** (Enterprise) - Exchange data

**Implementation Example** (Unusual Whales API):
```python
import requests

class UnusualWhalesProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.unusualwhales.com"

    def get_sweep_data(self, ticker: str) -> dict:
        response = requests.get(
            f"{self.base_url}/api/stock/{ticker}/options-flow",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        data = response.json()

        # Count aggressive orders (sweeps)
        sweeps = [
            order for order in data.get("orders", [])
            if order.get("is_sweep", False)
        ]

        return {
            "total_orders": len(data.get("orders", [])),
            "sweep_count": len(sweeps),
            "sweep_volume": sum(s.get("volume", 0) for s in sweeps),
            "has_unusual_sweeps": len(sweeps) > 5,
        }

# In Smart Money screener
if has_premium_data:
    sweep_data = unusual_whales.get_sweep_data(ticker)
    if not sweep_data["has_unusual_sweeps"]:
        continue  # Filter out stocks without sweep activity
```

**Impact**: ⭐⭐⭐⭐⭐ (Significantly improves Smart Money accuracy)
**Effort**: 2-3 hours (API integration)
**Cost**: $50-90/month
**Priority**: MEDIUM (valuable but adds cost)

---

### 8. Enhance Insider Buying Detection
**Problem**: Current implementation only checks net purchases > 0
**Solution**: Add insider buying quality metrics

**Implementation**:
```python
def get_analyst_and_insider_data(self, ticker: str) -> dict:
    # Current: Simple net purchases check
    net_purchases = purchases - sales  # ❌ Doesn't consider context

    # Enhanced: Add quality metrics
    insider_data = {
        "insider_net_purchases": net_purchases,
        "insider_purchase_count": len(purchase_transactions),
        "insider_avg_purchase_size": purchases / len(purchase_transactions),
        "insider_buying_trend": "increasing",  # Compare to previous period
        "c_suite_buying": False,  # CEO/CFO transactions only
        "director_buying": False,  # Board members only
        "open_market_buying": False,  # Exclude option exercises
        "cluster_buying": False,  # Multiple insiders buying same week
    }

    # Enhanced filtering
    if require_insider_buying:
        # Require meaningful buying, not just net positive
        if (insider_data["insider_net_purchases"] < 10000 or
            insider_data["insider_purchase_count"] < 2):
            continue

        # Bonus: Cluster buying (multiple insiders) is stronger signal
        if insider_data["cluster_buying"]:
            score += 10
```

**Impact**: ⭐⭐⭐⭐ (Higher quality Undiscovered results)
**Effort**: 2-3 hours
**Priority**: MEDIUM

---

## 🎨 User Experience Enhancements

### 9. Add Result Explanation
**Problem**: Users don't understand why stocks passed/failed
**Solution**: Add detailed explanations to results

**Implementation**:
```python
# Backend: Expand "reasons" field with more detail
result = StockScreenerResult(
    ticker=ticker,
    score=score,
    reasons=[
        f"✅ High call/put ratio: {call_to_put:.2f} (threshold: {min_call_to_put_ratio})",
        f"✅ Unusual volume: {total_vol:,} vs avg {avg_vol:,} ({total_vol/avg_vol:.1f}x)",
        f"📊 Institutional ownership: {inst_ownership:.1f}%",
        f"💰 Options premium: ${total_premium:,.0f}",
    ],
    # Add new field for detailed analysis
    analysis={
        "call_to_put_ratio": {
            "value": call_to_put,
            "threshold": min_call_to_put_ratio,
            "status": "pass" if call_to_put >= min_call_to_put_ratio else "fail",
            "interpretation": "Strong bullish conviction from options traders",
        },
        "unusual_volume": {
            "value": total_vol,
            "average": avg_vol,
            "multiplier": total_vol / avg_vol,
            "status": "pass",
            "interpretation": "Abnormally high options activity suggests impending move",
        },
    },
)
```

**Frontend**: Add expandable sections to show detailed analysis

**Impact**: ⭐⭐⭐⭐ (Better user understanding)
**Effort**: 3-4 hours
**Priority**: MEDIUM

---

### 10. Add Historical Screener Results
**Problem**: No way to see past screening results
**Solution**: Store and display historical screen results

**Implementation**:
```python
# Add database table for screener results
CREATE TABLE screener_results (
    id SERIAL PRIMARY KEY,
    screener_name VARCHAR(50),
    ticker VARCHAR(10),
    score FLOAT,
    criteria JSONB,
    metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

# In router endpoint
@router.get("/smart-money")
async def get_smart_money(...):
    results = run_screening_logic()

    # Save results to database
    for result in results:
        db.insert("screener_results", {
            "screener_name": "Smart Money",
            "ticker": result.ticker,
            "score": result.score,
            "criteria": criteria,
            "metrics": result.metrics,
        })

    return results

# Add new endpoint to retrieve historical results
@router.get("/smart-money/history")
async def get_smart_money_history(
    days: int = Query(7, ge=1, le=90),
):
    return db.query(
        "SELECT * FROM screener_results "
        "WHERE screener_name = 'Smart Money' "
        "AND created_at >= NOW() - INTERVAL '%s days' "
        "ORDER BY created_at DESC",
        days
    )
```

**Frontend Features**:
- View past results (7 days, 30 days, 90 days)
- Track which stocks repeatedly appear
- See how scores change over time
- "Watchlist" favorite stocks from past screens

**Impact**: ⭐⭐⭐⭐ (Enables trend analysis)
**Effort**: 6-8 hours (database + UI)
**Priority**: LOW (nice-to-have)

---

## 🔧 Technical Optimizations

### 11. Add Request Queuing
**Problem**: Multiple concurrent screeners cause resource contention
**Solution**: Queue screener jobs and process sequentially

**Implementation**:
```python
# Use Celery for background job processing
from celery import Celery

celery_app = Celery('screener', broker='redis://localhost:6379/0')

@celery_app.task
def run_screener_task(screener_type: str, params: dict) -> dict:
    """Run screener in background."""
    if screener_type == "smart_money":
        return run_smart_money_screener(**params)
    elif screener_type == "undiscovered":
        return run_undiscovered_screener(**params)

# In router endpoint
@router.post("/smart-money/async")
async def queue_smart_money(params: dict):
    # Queue the job
    task = run_screener_task.delay("smart_money", params)

    return {
        "job_id": task.id,
        "status": "queued",
        "message": "Screener job queued. Check /jobs/{job_id} for status."
    }

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    task = celery_app.AsyncResult(job_id)

    if task.ready():
        return {"status": "complete", "result": task.result}
    else:
        return {"status": "processing", "progress": task.info.get("progress", 0)}
```

**Benefits**:
- Prevents server overload from concurrent screens
- Enables longer-running screens without timeout
- Allows progress tracking
- Better resource management

**Impact**: ⭐⭐⭐ (Better scalability)
**Effort**: 8-12 hours (Celery setup + integration)
**Priority**: LOW (only needed at scale)

---

### 12. Optimize yfinance Rate Limiting
**Problem**: Conservative 0.2s sleep between ALL API calls
**Solution**: Smarter rate limiting based on endpoint type

**Implementation**:
```python
from collections import defaultdict
from time import time

class SmartRateLimiter:
    def __init__(self):
        self.call_times = defaultdict(list)
        # Different limits for different endpoint types
        self.limits = {
            "fundamentals": {"calls": 10, "per_seconds": 1},  # 10 calls/sec
            "options": {"calls": 5, "per_seconds": 1},  # 5 calls/sec (slower)
            "history": {"calls": 20, "per_seconds": 1},  # 20 calls/sec (faster)
        }

    async def acquire(self, endpoint_type: str):
        limit = self.limits[endpoint_type]
        now = time()

        # Remove calls outside the window
        self.call_times[endpoint_type] = [
            t for t in self.call_times[endpoint_type]
            if now - t < limit["per_seconds"]
        ]

        # Wait if at limit
        if len(self.call_times[endpoint_type]) >= limit["calls"]:
            oldest_call = self.call_times[endpoint_type][0]
            wait_time = limit["per_seconds"] - (now - oldest_call)
            await asyncio.sleep(wait_time)

        # Record this call
        self.call_times[endpoint_type].append(time())

# Usage
rate_limiter = SmartRateLimiter()

async def get_fundamentals(ticker: str):
    await rate_limiter.acquire("fundamentals")
    return yf.Ticker(ticker).info

async def get_options_flow(ticker: str):
    await rate_limiter.acquire("options")
    return yf.Ticker(ticker).options
```

**Performance Gain**: ~20% faster (34s → 27s)

**Impact**: ⭐⭐⭐
**Effort**: 2-3 hours
**Priority**: LOW (marginal improvement)

---

## 📈 Analytics & Monitoring

### 13. Add Screener Performance Metrics
**Problem**: No visibility into screener performance and accuracy
**Solution**: Track and visualize key metrics

**Metrics to Track**:
```python
# Add to Cloud Monitoring or custom dashboard
screener_metrics = {
    # Performance
    "execution_time_seconds": 37.2,
    "stocks_screened": 46,
    "stocks_passed": 0,
    "success_rate": 0.0,
    "average_score": None,

    # Data quality
    "api_errors": 2,
    "missing_data_count": 5,
    "cache_hit_rate": 0.45,

    # Business metrics
    "daily_active_users": 15,
    "screens_per_user": 3.2,
    "most_popular_universe": "popular",
    "most_popular_screener": "Lynch Fundamentals",
}

# Log metrics after each screen
logger.info("Screener metrics", extra=screener_metrics)

# Create dashboard in GCP Monitoring
# - Execution time trends
# - Success rate over time
# - Most popular filters
# - Error rates by ticker
```

**Impact**: ⭐⭐⭐ (Better operational visibility)
**Effort**: 3-4 hours
**Priority**: LOW

---

### 14. Add Backtesting Framework
**Problem**: Can't validate if screener criteria actually work
**Solution**: Backtest screener performance on historical data

**Implementation**:
```python
@router.post("/smart-money/backtest")
async def backtest_smart_money(
    start_date: str,
    end_date: str,
    holding_period_days: int = 30,
):
    """
    Backtest Smart Money screener by running it on historical dates
    and tracking forward returns.
    """
    results = []
    current_date = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    while current_date < end:
        # Run screener with historical data
        screen_results = run_screener_at_date(current_date)

        # Track performance over holding period
        for stock in screen_results:
            entry_price = get_price_at_date(stock.ticker, current_date)
            exit_price = get_price_at_date(
                stock.ticker,
                current_date + timedelta(days=holding_period_days)
            )

            return_pct = ((exit_price - entry_price) / entry_price) * 100

            results.append({
                "date": current_date,
                "ticker": stock.ticker,
                "score": stock.score,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return_pct": return_pct,
            })

        # Move to next week
        current_date += timedelta(days=7)

    # Calculate aggregate statistics
    avg_return = sum(r["return_pct"] for r in results) / len(results)
    win_rate = len([r for r in results if r["return_pct"] > 0]) / len(results)

    return {
        "total_signals": len(results),
        "average_return": avg_return,
        "win_rate": win_rate,
        "results": results,
    }
```

**Impact**: ⭐⭐⭐⭐⭐ (Validates strategy effectiveness)
**Effort**: 12-16 hours (requires historical data)
**Priority**: LOW (advanced feature)

---

## 🎁 Feature Additions

### 15. Add "Save Filter Presets"
**Problem**: Users must reconfigure filters each time
**Solution**: Allow saving and loading custom filter presets

**Implementation**:
```python
# Database table
CREATE TABLE user_filter_presets (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    screener_type VARCHAR(50),
    preset_name VARCHAR(100),
    filters JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

# Save preset endpoint
@router.post("/presets")
async def save_preset(
    user_id: str,
    preset_name: str,
    screener_type: str,
    filters: dict,
):
    db.insert("user_filter_presets", {
        "user_id": user_id,
        "screener_type": screener_type,
        "preset_name": preset_name,
        "filters": json.dumps(filters),
    })
    return {"status": "saved"}

# Load presets endpoint
@router.get("/presets")
async def get_user_presets(user_id: str):
    return db.query(
        "SELECT * FROM user_filter_presets WHERE user_id = %s",
        user_id
    )
```

**Frontend**: Add "Save", "Load", "Delete" buttons for presets

**Impact**: ⭐⭐⭐⭐ (Better UX for power users)
**Effort**: 4-6 hours
**Priority**: LOW

---

### 16. Add Email/Webhook Alerts
**Problem**: Users must manually check for new screening results
**Solution**: Send alerts when criteria match

**Implementation**:
```python
# Add alert configuration table
CREATE TABLE screener_alerts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    screener_type VARCHAR(50),
    filters JSONB,
    notification_method VARCHAR(20),  -- 'email' or 'webhook'
    notification_target VARCHAR(200),  -- email address or webhook URL
    frequency VARCHAR(20),  -- 'daily', 'weekly', 'immediate'
    last_run TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

# Background job to check alerts
@celery_app.task
def process_screener_alerts():
    alerts = db.query("SELECT * FROM screener_alerts WHERE active = TRUE")

    for alert in alerts:
        # Run the screener
        results = run_screener(alert.screener_type, alert.filters)

        # Send notification if results found
        if results:
            if alert.notification_method == "email":
                send_email(
                    to=alert.notification_target,
                    subject=f"Screener Alert: {len(results)} stocks match",
                    body=format_results_email(results)
                )
            elif alert.notification_method == "webhook":
                requests.post(
                    alert.notification_target,
                    json={"results": results}
                )

# Schedule daily alert processing
celery_app.conf.beat_schedule = {
    'process-alerts-daily': {
        'task': 'process_screener_alerts',
        'schedule': crontab(hour=9, minute=0),  # Run at 9 AM daily
    },
}
```

**Impact**: ⭐⭐⭐⭐ (Great for active traders)
**Effort**: 6-10 hours
**Priority**: LOW

---

## 📋 Summary & Recommendations

### Immediate Actions (Do First)
| # | Improvement | Impact | Effort | Priority |
|---|-------------|--------|--------|----------|
| 2 | Reduce default universe / add limit | ⭐⭐⭐⭐⭐ | 30 min | HIGH |
| 3 | Relax default filters / add presets | ⭐⭐⭐⭐⭐ | 1-2 hrs | HIGH |
| 1 | Add progress indicators | ⭐⭐⭐⭐⭐ | 2-4 hrs | HIGH |

### Short-term (Next Sprint)
| # | Improvement | Impact | Effort | Priority |
|---|-------------|--------|--------|----------|
| 8 | Enhance insider buying detection | ⭐⭐⭐⭐ | 2-3 hrs | MEDIUM |
| 9 | Add result explanations | ⭐⭐⭐⭐ | 3-4 hrs | MEDIUM |
| 4 | Add data caching (Redis) | ⭐⭐⭐⭐ | 3-4 hrs | MEDIUM |

### Medium-term (Future Iterations)
| # | Improvement | Impact | Effort | Priority |
|---|-------------|--------|--------|----------|
| 5 | Parallelize API calls | ⭐⭐⭐⭐⭐ | 4-6 hrs | MEDIUM |
| 7 | Add sweep detection (premium) | ⭐⭐⭐⭐⭐ | 2-3 hrs + $50/mo | MEDIUM |
| 15 | Save filter presets | ⭐⭐⭐⭐ | 4-6 hrs | LOW |

### Long-term (Advanced Features)
| # | Improvement | Impact | Effort | Priority |
|---|-------------|--------|--------|----------|
| 14 | Add backtesting framework | ⭐⭐⭐⭐⭐ | 12-16 hrs | LOW |
| 10 | Historical screener results | ⭐⭐⭐⭐ | 6-8 hrs | LOW |
| 16 | Email/webhook alerts | ⭐⭐⭐⭐ | 6-10 hrs | LOW |

---

## 🚀 Quick Start Recommendations

If you want to see improvements quickly, start with these:

**Week 1: Quick Wins**
1. Change default universe from "popular" (46) to "tech" (31) - **5 min**
2. Add `limit` parameter to endpoints - **30 min**
3. Create "aggressive", "moderate", "strict" presets - **1 hour**
4. Deploy and test

**Expected Result**: Screeners return in 20-25 seconds with better results

**Week 2: UX Improvements**
1. Add progress indicators (SSE or polling) - **3-4 hours**
2. Add detailed explanations to results - **3-4 hours**

**Expected Result**: Users see real-time progress and understand why stocks passed/failed

**Week 3: Performance**
1. Implement Redis caching - **4 hours**
2. Parallelize API calls (5 concurrent) - **6 hours**

**Expected Result**: Screeners complete in 7-10 seconds (cached: 2-3 seconds)

---

**Document Version**: 1.0
**Created**: 2025-11-10
**Last Updated**: 2025-11-10
**Maintainer**: Development Team
