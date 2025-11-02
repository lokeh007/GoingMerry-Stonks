"""
Services Package.

This package contains business logic and external service integrations
for the GoingMerry-Stonks platform.
"""

from .market_data import MarketDataProvider

__all__ = ["MarketDataProvider"]
