"""
Services Package.

This package contains business logic and external service integrations
for the GoingMerry-Stonks platform.

To avoid circular imports and dependency issues, modules are not automatically imported.
Import explicitly as needed:
    from app.services.market_data import MarketDataProvider
    from app.services.yfinance_provider import YFinanceProvider
    from app.services.rate_limiter import TokenBucket  # Thread-safe rate limiting utility

Note:
    The TokenBucket class is available in app.services.rate_limiter for both
    production and testing purposes. It provides a thread-safe token bucket
    rate limiter that can be used by any service requiring rate limiting.
"""

# No __all__ - use explicit imports as documented above
