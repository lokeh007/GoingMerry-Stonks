"""
Tests for screener router endpoints.

Tests Lynch Fast Growers screener and stock screening functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.mark.unit
def test_list_screeners(test_client: TestClient):
    """Test listing available screeners."""
    response = test_client.get("/api/screener/screeners")

    assert response.status_code == 200
    data = response.json()
    assert "screeners" in data
    assert "total_screeners" in data
    assert data["total_screeners"] > 0

    # Verify Lynch Fast Growers is listed
    screeners = data["screeners"]
    lynch_screener = next((s for s in screeners if "Lynch" in s["name"]), None)
    assert lynch_screener is not None
    assert lynch_screener["endpoint"] == "/api/screener/lynch-fast-growers"


@pytest.mark.unit
def test_lynch_fast_growers_default_params(test_client: TestClient, sample_stock_financials):
    """Test Lynch Fast Growers screener with default parameters."""
    with patch('app.services.market_data.MarketDataProvider.get_stock_universe') as mock_universe, \
         patch('app.services.market_data.MarketDataProvider.get_stock_financials') as mock_financials, \
         patch('app.services.market_data.MarketDataProvider.get_ticker_details') as mock_details:

        # Mock stock universe
        mock_universe.return_value = ["NVDA", "AAPL"]

        # Mock financial data
        mock_financials.return_value = sample_stock_financials

        # Mock ticker details
        mock_details.return_value = {
            "name": "NVIDIA Corporation",
            "sector": "Technology"
        }

        response = test_client.get("/api/screener/lynch-fast-growers")

        assert response.status_code == 200
        data = response.json()
        assert data["screener_name"] == "Lynch Fast Growers"
        assert "results" in data
        assert "criteria" in data
        assert "total_results" in data


@pytest.mark.unit
def test_lynch_fast_growers_custom_params(test_client: TestClient, sample_stock_financials):
    """Test Lynch Fast Growers screener with custom parameters."""
    with patch('app.services.market_data.MarketDataProvider.get_stock_universe') as mock_universe, \
         patch('app.services.market_data.MarketDataProvider.get_stock_financials') as mock_financials, \
         patch('app.services.market_data.MarketDataProvider.get_ticker_details') as mock_details:

        mock_universe.return_value = ["NVDA"]
        mock_financials.return_value = sample_stock_financials
        mock_details.return_value = {"name": "NVIDIA Corporation", "sector": "Technology"}

        response = test_client.get(
            "/api/screener/lynch-fast-growers?"
            "min_earnings_growth=20&"
            "max_peg_ratio=1.5&"
            "max_debt_to_equity=0.5&"
            "limit=5"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["criteria"]["min_earnings_growth"] == 20.0
        assert data["criteria"]["max_peg_ratio"] == 1.5


@pytest.mark.unit
def test_lynch_fast_growers_filtering(test_client: TestClient):
    """Test that Lynch screener properly filters stocks."""
    with patch('app.services.yfinance_provider.YFinanceProvider.get_stock_universe') as mock_universe, \
         patch('app.services.yfinance_provider.YFinanceProvider.get_fundamentals') as mock_fundamentals:

        mock_universe.return_value = ["GOOD", "BAD"]

        # Mock different financials for each stock
        def get_fundamentals(ticker):
            if ticker == "GOOD":
                return {
                    "ticker": "GOOD",
                    "company_name": "Good Company",
                    "sector": "Tech",
                    "peg_ratio": 0.8,
                    "eps_growth": 22.0,
                    "debt_to_equity": 0.3,
                    "current_ratio": 2.0,
                    "market_cap": 10.0,
                    "current_price": 100.0,
                    "pe_ratio": 18.0,
                    "revenue_growth": 15.0,
                    "roe": 20.0,
                    "institutional_ownership": 50.0,
                    "week_52_low": 80.0,
                    "week_52_high": 120.0,
                    "timestamp": "2025-11-09"
                }
            else:
                return {
                    "ticker": "BAD",
                    "company_name": "Bad Company",
                    "sector": "Tech",
                    "peg_ratio": 3.0,  # Too high
                    "eps_growth": 5.0,  # Too low
                    "debt_to_equity": 0.3,
                    "current_ratio": 2.0,
                    "market_cap": 10.0,
                    "current_price": 100.0,
                    "pe_ratio": 25.0,
                    "revenue_growth": 5.0,
                    "roe": 10.0,
                    "institutional_ownership": 60.0,
                    "week_52_low": 90.0,
                    "week_52_high": 110.0,
                    "timestamp": "2025-11-09"
                }

        mock_fundamentals.side_effect = get_fundamentals

        response = test_client.get("/api/screener/lynch-fast-growers")

        assert response.status_code == 200
        data = response.json()

        # Only GOOD should pass the screening
        tickers = [r["ticker"] for r in data["results"]]
        assert "GOOD" in tickers
        assert "BAD" not in tickers


@pytest.mark.unit
def test_lynch_score_calculation():
    """Test Lynch scoring algorithm."""
    from app.routers.screener import _calculate_lynch_score

    # Excellent stock
    excellent_financials = {
        "peg_ratio": 0.4,
        "eps_growth": 23.0,
        "debt_to_equity": 0.2,
        "current_ratio": 3.0
    }
    excellent_score = _calculate_lynch_score(excellent_financials)
    assert excellent_score >= 90

    # Average stock - adjusted for realistic average scoring
    average_financials = {
        "peg_ratio": 1.0,
        "eps_growth": 18.0,
        "debt_to_equity": 0.7,
        "current_ratio": 1.8
    }
    average_score = _calculate_lynch_score(average_financials)
    assert 50 <= average_score < 80

    # Poor stock
    poor_financials = {
        "peg_ratio": 2.5,
        "eps_growth": 8.0,
        "debt_to_equity": 2.0,
        "current_ratio": 0.8
    }
    poor_score = _calculate_lynch_score(poor_financials)
    assert poor_score < 50


@pytest.mark.unit
def test_screening_reasons_generation():
    """Test that screening reasons are properly generated."""
    from app.routers.screener import _generate_screening_reasons

    financials = {
        "peg_ratio": 0.75,
        "eps_growth": 25.0,
        "debt_to_equity": 0.3,
        "current_ratio": 2.5,
        "revenue_growth": 20.0
    }

    reasons = _generate_screening_reasons(financials)

    assert len(reasons) > 0
    assert any("PEG" in reason for reason in reasons)
    assert any("growth" in reason.lower() for reason in reasons)


@pytest.mark.unit
def test_screener_validation_errors(test_client: TestClient):
    """Test screener parameter validation."""
    # Negative growth rate (invalid)
    response = test_client.get("/api/screener/lynch-fast-growers?min_earnings_growth=-10")
    assert response.status_code == 422

    # Limit too high
    response = test_client.get("/api/screener/lynch-fast-growers?limit=1000")
    assert response.status_code == 422


@pytest.mark.integration
def test_screener_handles_api_failures(test_client: TestClient):
    """Test screener handles API failures gracefully."""
    with patch('app.services.market_data.MarketDataProvider.get_stock_universe') as mock_universe, \
         patch('app.services.market_data.MarketDataProvider.get_stock_financials') as mock_financials:

        mock_universe.return_value = ["AAPL", "NVDA"]

        # Simulate API failure for one stock
        from app.services.market_data import MarketDataError
        mock_financials.side_effect = MarketDataError("API Error")

        response = test_client.get("/api/screener/lynch-fast-growers")

        # Should still return 200 with empty or partial results
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


@pytest.mark.security
def test_screener_no_sql_injection(test_client: TestClient):
    """Test that screener is not vulnerable to SQL injection."""
    # Attempt SQL injection in parameters
    malicious_input = "'; DROP TABLE stocks; --"

    response = test_client.get(f"/api/screener/lynch-fast-growers?universe={malicious_input}")

    # Should handle safely (validation error or safe processing)
    assert response.status_code in [200, 422]
