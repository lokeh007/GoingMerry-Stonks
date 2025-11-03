"""
Additional tests for market_data service to boost coverage to 70%.
Focuses on simpler methods and edge cases.
"""
import pytest
from app.services.market_data import MarketDataProvider, InvalidTickerError


@pytest.mark.unit
def test_get_stock_universe_popular():
    """Test stock universe for popular stocks."""
    provider = MarketDataProvider(api_key="test_key")
    result = provider.get_stock_universe("popular")

    assert isinstance(result, list)
    assert len(result) > 0
    assert "AAPL" in result
    assert "MSFT" in result
    assert "GOOGL" in result


@pytest.mark.unit
def test_get_stock_universe_sp500():
    """Test stock universe for S&P 500 stocks."""
    provider = MarketDataProvider(api_key="test_key")
    result = provider.get_stock_universe("sp500")

    assert isinstance(result, list)
    # Just verify it returns a list, don't check length
    assert all(isinstance(ticker, str) for ticker in result)


@pytest.mark.unit
def test_get_stock_universe_tech():
    """Test stock universe for tech stocks."""
    provider = MarketDataProvider(api_key="test_key")
    result = provider.get_stock_universe("tech")

    assert isinstance(result, list)
    assert "AAPL" in result
    assert "MSFT" in result
    assert "NVDA" in result


@pytest.mark.unit
def test_get_stock_universe_default():
    """Test stock universe with default parameter."""
    provider = MarketDataProvider(api_key="test_key")
    result = provider.get_stock_universe()

    # Should default to popular
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.unit
def test_get_empty_financials_structure():
    """Test _get_empty_financials returns correct structure."""
    provider = MarketDataProvider(api_key="test_key")
    result = provider._get_empty_financials("TEST")

    # Verify all expected keys are present
    expected_keys = [
        "ticker", "price", "market_cap", "pe_ratio", "peg_ratio",
        "revenue_growth", "eps_growth", "eps",
        "debt_to_equity", "current_ratio"
    ]

    for key in expected_keys:
        assert key in result, f"Missing key: {key}"

    assert result["ticker"] == "TEST"
    assert result["price"] is None
    assert result["market_cap"] is None


@pytest.mark.unit
def test_option_chain_invalid_empty_ticker():
    """Test option chain rejects empty ticker."""
    provider = MarketDataProvider(api_key="test_key")

    with pytest.raises(InvalidTickerError, match="non-empty string"):
        provider.get_option_chain("")


@pytest.mark.unit
def test_option_chain_invalid_none_ticker():
    """Test option chain rejects None ticker."""
    provider = MarketDataProvider(api_key="test_key")

    with pytest.raises(InvalidTickerError):
        provider.get_option_chain(None)


@pytest.mark.unit
def test_option_chain_invalid_non_string():
    """Test option chain rejects non-string ticker."""
    provider = MarketDataProvider(api_key="test_key")

    with pytest.raises(InvalidTickerError):
        provider.get_option_chain(12345)


@pytest.mark.unit
def test_provider_with_custom_timeout():
    """Test provider initialization with custom timeout."""
    provider = MarketDataProvider(api_key="test_key", timeout=45)

    assert provider.timeout == 45
    assert provider.api_key == "test_key"


@pytest.mark.unit
def test_provider_base_url():
    """Test provider has correct base URL."""
    provider = MarketDataProvider(api_key="test_key")

    assert "polygon.io" in provider.base_url
    assert provider.base_url.startswith("https://")


@pytest.mark.unit
def test_stock_universe_returns_unique_tickers():
    """Test stock universe returns unique ticker symbols."""
    provider = MarketDataProvider(api_key="test_key")
    result = provider.get_stock_universe("popular")

    # Should not have duplicates
    assert len(result) == len(set(result))


@pytest.mark.unit
def test_stock_universe_all_uppercase():
    """Test stock universe tickers are all uppercase."""
    provider = MarketDataProvider(api_key="test_key")
    result = provider.get_stock_universe("tech")

    for ticker in result:
        assert ticker.isupper()
        assert isinstance(ticker, str)
        assert len(ticker) >= 1


@pytest.mark.unit
def test_empty_financials_all_none_except_ticker():
    """Test empty financials has None for all numeric fields."""
    provider = MarketDataProvider(api_key="test_key")
    result = provider._get_empty_financials("TSLA")

    assert result["ticker"] == "TSLA"

    # All other fields should be None
    numeric_fields = [
        "price", "market_cap", "pe_ratio", "peg_ratio",
        "revenue_growth", "eps_growth", "eps",
        "debt_to_equity", "current_ratio"
    ]

    for field in numeric_fields:
        assert result[field] is None, f"{field} should be None"
