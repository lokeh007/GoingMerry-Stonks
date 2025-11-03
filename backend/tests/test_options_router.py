"""
Tests for options router endpoints.

Tests option chain retrieval, validation, and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.mark.unit
def test_get_option_chain_success(test_client: TestClient, mock_polygon_api, sample_option_chain):
    """Test successful option chain retrieval."""
    # Configure mock to return option chain data
    mock_polygon_api.return_value.json.return_value = {
        "status": "OK",
        "results": [
            {
                "ticker": "O:AAPL250117C00150000",
                "strike_price": 150.0,
                "expiration_date": "2025-01-17",
                "contract_type": "call"
            }
        ]
    }

    with patch('app.services.market_data.MarketDataProvider.get_option_chain') as mock_chain:
        mock_chain.return_value = sample_option_chain

        response = test_client.get("/options/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert "calls" in data
        assert "puts" in data
        assert data["total_contracts"] >= 0


@pytest.mark.unit
def test_get_option_chain_with_expiration_filter(test_client: TestClient, sample_option_chain):
    """Test option chain with expiration date filter."""
    with patch('app.services.market_data.MarketDataProvider.get_option_chain') as mock_chain:
        mock_chain.return_value = sample_option_chain

        response = test_client.get("/options/AAPL?expiration_date=2025-01-17")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"


@pytest.mark.unit
def test_get_option_chain_with_limit(test_client: TestClient, sample_option_chain):
    """Test option chain with limit parameter."""
    with patch('app.services.market_data.MarketDataProvider.get_option_chain') as mock_chain:
        mock_chain.return_value = sample_option_chain

        response = test_client.get("/options/AAPL?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total_contracts"] <= 10


@pytest.mark.unit
def test_get_option_chain_invalid_ticker(test_client: TestClient):
    """Test option chain with invalid ticker returns 404."""
    with patch('app.services.market_data.MarketDataProvider.get_option_chain') as mock_chain:
        from app.services.market_data import InvalidTickerError
        mock_chain.side_effect = InvalidTickerError("Ticker not found")

        response = test_client.get("/options/INVALID")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit
def test_get_option_chain_rate_limit(test_client: TestClient):
    """Test option chain returns 429 on rate limit."""
    with patch('app.services.market_data.MarketDataProvider.get_option_chain') as mock_chain:
        from app.services.market_data import RateLimitError
        mock_chain.side_effect = RateLimitError("Rate limit exceeded")

        response = test_client.get("/options/AAPL")

        assert response.status_code == 429


@pytest.mark.unit
def test_get_option_chain_api_error(test_client: TestClient):
    """Test option chain handles API errors gracefully."""
    with patch('app.services.market_data.MarketDataProvider.get_option_chain') as mock_chain:
        from app.services.market_data import APIConnectionError
        mock_chain.side_effect = APIConnectionError("Connection failed")

        response = test_client.get("/options/AAPL")

        assert response.status_code == 503


@pytest.mark.unit
def test_get_option_chain_summary(test_client: TestClient, sample_option_chain):
    """Test option chain summary endpoint."""
    with patch('app.services.market_data.MarketDataProvider.get_option_chain') as mock_chain:
        mock_chain.return_value = sample_option_chain

        response = test_client.get("/options/AAPL/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total_contracts" in data
        assert "calls_count" in data
        assert "puts_count" in data


@pytest.mark.unit
def test_option_chain_validation():
    """Test option chain data validation with Pydantic."""
    from app.models.options import OptionContract, OptionType

    # Valid option contract
    contract = OptionContract(
        ticker="O:AAPL250117C00150000",
        strike=150.0,
        expiration_date="2025-01-17",
        option_type=OptionType.CALL,
        last_price=5.25,
        bid=5.20,
        ask=5.30,
        volume=1000,
        open_interest=5000
    )

    assert contract.strike == 150.0
    assert contract.option_type == OptionType.CALL

    # Test validation failure
    with pytest.raises(Exception):
        OptionContract(
            ticker="INVALID",
            strike=-10.0,  # Invalid negative strike
            expiration_date="2025-01-17",
            option_type=OptionType.CALL
        )


@pytest.mark.integration
def test_option_chain_real_api_call(test_client: TestClient):
    """
    Integration test with real Polygon API.

    Note: This test is skipped in CI/CD if API key is not available.
    """
    import os
    if os.getenv("POLYGON_API_KEY") == "test_api_key_12345":
        pytest.skip("Skipping real API test in test environment")

    response = test_client.get("/options/AAPL?limit=5")

    # Should succeed or fail gracefully
    assert response.status_code in [200, 404, 429, 503]
