"""
Tests for technical analysis router endpoints.

Tests Gann Square of 9 endpoint with reference price validation.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.mark.unit
def test_gann_extreme_reference_price_blocked_by_default(test_client: TestClient):
    """Test that extreme reference prices are blocked by default."""
    # Mock the fundamentals to return a current price
    mock_fundamentals = {
        "current_price": 100.0,
        "week_52_low": 80.0,
        "week_52_high": 120.0,
    }

    with patch('app.services.yfinance_provider.YFinanceProvider.get_fundamentals') as mock_fund:
        mock_fund.return_value = mock_fundamentals

        # Try to use reference price >2x current price (should fail)
        response = test_client.get(
            "/api/technical/AAPL/gann?reference_price=250.0"
        )

        assert response.status_code == 400
        assert "more than 2x" in response.json()["detail"]
        assert "allow_extreme_reference_price=true" in response.json()["detail"]


@pytest.mark.unit
def test_gann_extreme_reference_price_allowed_with_flag(test_client: TestClient):
    """Test that extreme reference prices are allowed when flag is set."""
    # Mock the fundamentals
    mock_fundamentals = {
        "current_price": 100.0,
        "week_52_low": 80.0,
        "week_52_high": 120.0,
    }

    # Mock the Gann calculator
    mock_gann_levels = {
        "support_levels": [95.0, 90.0, 85.0],
        "resistance_levels": [105.0, 110.0, 115.0],
        "nearest_support": 95.0,
        "nearest_resistance": 105.0,
        "current_position": "between_levels",
    }

    with patch('app.services.yfinance_provider.YFinanceProvider.get_fundamentals') as mock_fund, \
         patch('app.financial_models.gann.GannSquareCalculator.calculate_gann_levels') as mock_calc, \
         patch('app.financial_models.gann.GannSquareCalculator.is_at_key_level') as mock_key:

        mock_fund.return_value = mock_fundamentals
        mock_calc.return_value = mock_gann_levels
        mock_key.return_value = {"at_support": False, "at_resistance": False}

        # Use reference price >2x current price WITH flag (should succeed)
        response = test_client.get(
            "/api/technical/AAPL/gann?reference_price=250.0&allow_extreme_reference_price=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["current_price"] == 100.0
        assert data["reference_price"] == 250.0


@pytest.mark.unit
def test_gann_normal_reference_price_works(test_client: TestClient):
    """Test that normal reference prices work without flag."""
    # Mock the fundamentals
    mock_fundamentals = {
        "current_price": 100.0,
        "week_52_low": 80.0,
        "week_52_high": 120.0,
    }

    # Mock the Gann calculator
    mock_gann_levels = {
        "support_levels": [95.0, 90.0, 85.0],
        "resistance_levels": [105.0, 110.0, 115.0],
        "nearest_support": 95.0,
        "nearest_resistance": 105.0,
        "current_position": "between_levels",
    }

    with patch('app.services.yfinance_provider.YFinanceProvider.get_fundamentals') as mock_fund, \
         patch('app.financial_models.gann.GannSquareCalculator.calculate_gann_levels') as mock_calc, \
         patch('app.financial_models.gann.GannSquareCalculator.is_at_key_level') as mock_key:

        mock_fund.return_value = mock_fundamentals
        mock_calc.return_value = mock_gann_levels
        mock_key.return_value = {"at_support": False, "at_resistance": False}

        # Use normal reference price (should work fine)
        response = test_client.get(
            "/api/technical/AAPL/gann?reference_price=90.0"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["current_price"] == 100.0
        assert data["reference_price"] == 90.0
