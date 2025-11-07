"""
Pytest configuration and shared fixtures for GoingMerry-Stonks tests.

This module provides common fixtures and configuration for all tests.
"""

import os
from typing import Generator, Dict, Any
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Set test environment variables before importing app
os.environ["POLYGON_API_KEY"] = "test_api_key_12345"
os.environ["ENVIRONMENT"] = "test"

from app.main import app  # noqa: E402


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """
    Fixture providing FastAPI test client.

    Yields:
        TestClient: Configured test client for API testing
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_polygon_api():
    """
    Mock Polygon.io API responses for testing.

    Returns:
        Mock: Configured mock for Polygon API
    """
    with patch('app.services.market_data.requests.get') as mock_get:
        # Configure default successful response for aggregate endpoint
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "c": 150.25,  # close price
                    "o": 149.00,  # open price
                    "h": 152.00,  # high price
                    "l": 148.00,  # low price
                    "v": 1000000,  # volume
                    "t": 1700000000000,  # timestamp
                }
            ]
        }
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def sample_option_chain() -> Dict[str, Any]:
    """
    Sample option chain data for testing.

    Returns:
        dict: Mock option chain response
    """
    return {
        "ticker": "AAPL",
        "stock_price": 150.25,
        "calls": [
            {
                "ticker": "O:AAPL250117C00150000",
                "strike": 150.0,
                "expiration_date": "2025-01-17",
                "last_price": 5.25,
                "bid": 5.20,
                "ask": 5.30,
                "volume": 1500,
                "open_interest": 10000,
                "implied_volatility": 0.25,
                "delta": 0.55,
                "gamma": 0.05,
                "theta": -0.15,
                "vega": 0.35
            }
        ],
        "puts": [
            {
                "ticker": "O:AAPL250117P00150000",
                "strike": 150.0,
                "expiration_date": "2025-01-17",
                "last_price": 4.75,
                "bid": 4.70,
                "ask": 4.80,
                "volume": 1200,
                "open_interest": 8000,
                "implied_volatility": 0.23,
                "delta": -0.45,
                "gamma": 0.05,
                "theta": -0.12,
                "vega": 0.33
            }
        ],
        "total_contracts": 2,
        "timestamp": "2025-01-15T10:30:00"
    }


@pytest.fixture
def sample_stock_financials() -> Dict[str, Any]:
    """
    Sample stock financial data for testing screener.

    Returns:
        dict: Mock financial data
    """
    return {
        "ticker": "NVDA",
        "price": 495.22,
        "pe_ratio": 65.3,
        "peg_ratio": 1.8,
        "eps": 7.58,
        "eps_growth": 25.2,
        "revenue_growth": 125.5,
        "debt_to_equity": 0.45,
        "current_ratio": 3.45,
        "market_cap": 1200.5,
        "net_income": 10000000000,
        "revenues": 50000000000
    }


@pytest.fixture
def mock_database():
    """
    Mock database connection for testing.

    Returns:
        Mock: Configured database mock
    """
    # TODO: Implement when database integration is added
    pass


@pytest.fixture(autouse=True)
def reset_environment():
    """
    Reset environment variables after each test.

    This fixture automatically runs after each test to clean up.
    """
    yield
    # Cleanup code runs after test
    os.environ["ENVIRONMENT"] = "test"
