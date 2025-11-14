"""
Services Package.

This package contains business logic and external service integrations
for the GoingMerry-Stonks platform.

To avoid circular imports and dependency issues, modules are not automatically imported.
Import explicitly as needed:
    from app.services.market_data import MarketDataProvider
    from app.services.yfinance_provider import YFinanceProvider
    from app.services.rate_limiter import TokenBucket
"""

__all__ = ["MarketDataProvider", "YFinanceProvider", "TokenBucket"]
