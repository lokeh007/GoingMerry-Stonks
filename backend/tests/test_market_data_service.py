"""
Tests for market data service.

Tests Polygon.io API integration and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.market_data import (
    MarketDataProvider,
    MarketDataError,
    InvalidTickerError,
    RateLimitError,
    APIConnectionError
)


@pytest.mark.unit
def test_market_data_provider_initialization():
    """Test MarketDataProvider initialization."""
    provider = MarketDataProvider(api_key="test_key")
    assert provider.api_key == "test_key"
    assert provider.base_url == "https://api.polygon.io"
    assert provider.timeout == 10


@pytest.mark.unit
def test_market_data_provider_missing_api_key():
    """Test initialization fails without API key."""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="API key not found"):
            MarketDataProvider()


@pytest.mark.unit
def test_get_stock_quote_success(mock_polygon_api):
    """Test successful stock quote retrieval."""
    provider = MarketDataProvider(api_key="test_key")

    quote = provider.get_stock_quote("AAPL")

    assert quote["ticker"] == "AAPL"
    assert "price" in quote
    assert "volume" in quote
    assert quote["price"] > 0


@pytest.mark.unit
def test_get_stock_quote_invalid_ticker():
    """Test stock quote with invalid ticker."""
    with patch('app.services.market_data.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        provider = MarketDataProvider(api_key="test_key")

        with pytest.raises(InvalidTickerError):
            provider.get_stock_quote("INVALID")


@pytest.mark.unit
def test_get_stock_quote_rate_limit():
    """Test stock quote handles rate limiting."""
    with patch('app.services.market_data.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        provider = MarketDataProvider(api_key="test_key")

        with pytest.raises(RateLimitError):
            provider.get_stock_quote("AAPL")


@pytest.mark.unit
def test_get_stock_quote_api_auth_failure():
    """Test stock quote handles authentication failure."""
    with patch('app.services.market_data.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        provider = MarketDataProvider(api_key="invalid_key")

        with pytest.raises(APIConnectionError, match="authentication"):
            provider.get_stock_quote("AAPL")


@pytest.mark.unit
def test_get_stock_universe():
    """Test stock universe retrieval."""
    provider = MarketDataProvider(api_key="test_key")

    # Test different universe types
    popular = provider.get_stock_universe("popular")
    assert len(popular) > 0
    assert "AAPL" in popular
    assert "MSFT" in popular

    tech = provider.get_stock_universe("tech")
    assert len(tech) > 0
    assert "NVDA" in tech

    # Unknown universe returns default
    default = provider.get_stock_universe("unknown")
    assert len(default) > 0


@pytest.mark.unit
def test_health_check_success():
    """Test health check returns True on success."""
    with patch('app.services.market_data.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        provider = MarketDataProvider(api_key="test_key")
        assert provider.health_check() is True


@pytest.mark.unit
def test_health_check_failure():
    """Test health check returns False on failure."""
    with patch('app.services.market_data.requests.get') as mock_get:
        mock_get.side_effect = Exception("Connection failed")

        provider = MarketDataProvider(api_key="test_key")
        assert provider.health_check() is False


@pytest.mark.security
def test_api_key_not_logged():
    """Test that API key is not exposed in logs or errors."""
    with patch('app.services.market_data.requests.get') as mock_get:
        mock_get.side_effect = Exception("API Error")

        provider = MarketDataProvider(api_key="secret_api_key_12345")

        try:
            provider.get_stock_quote("AAPL")
        except Exception as e:
            error_message = str(e)
            assert "secret_api_key" not in error_message.lower()


@pytest.mark.unit
def test_timeout_configuration():
    """Test custom timeout configuration."""
    provider = MarketDataProvider(api_key="test_key", timeout=30)
    assert provider.timeout == 30


@pytest.mark.slow
@pytest.mark.integration
def test_real_api_connection():
    """
    Integration test with real API (skipped in CI).

    Tests actual connection to Polygon.io API.
    """
    import os
    if os.getenv("POLYGON_API_KEY") == "test_api_key_12345":
        pytest.skip("Skipping real API test")

    provider = MarketDataProvider()

    # Should not raise exception
    health = provider.health_check()
    assert isinstance(health, bool)
