"""
Market Data Service Module.

This module provides integration with Polygon.io API and yfinance for
market data retrieval. Uses yfinance for option chain data (free, 15-min delay)
and Polygon.io for stock quotes and fundamentals.
"""

import os
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging

import requests  # type: ignore
from requests.exceptions import (  # type: ignore
    RequestException,
    Timeout,
    HTTPError,
)
import yfinance as yf


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketDataError(Exception):
    """Base exception for market data operations."""

    pass


class APIConnectionError(MarketDataError):
    """Raised when unable to connect to the API."""

    pass


class InvalidTickerError(MarketDataError):
    """Raised when an invalid ticker symbol is provided."""

    pass


class RateLimitError(MarketDataError):
    """Raised when API rate limit is exceeded."""

    pass


class MarketDataProvider:
    """
    Service class for interacting with Polygon.io API.

    This class handles all communication with the Polygon.io API,
    including fetching stock quotes, historical data, and handling
    authentication and error scenarios.

    Attributes:
        api_key (str): Polygon.io API key from environment variables.
        base_url (str): Base URL for Polygon.io API.
        timeout (int): Request timeout in seconds.
    """

    BASE_URL = "https://api.polygon.io"
    DEFAULT_TIMEOUT = 10  # seconds

    def __init__(self, api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the MarketDataProvider.

        Args:
            api_key: Polygon.io API key. If not provided, reads from
                    POLYGON_API_KEY environment variable.
            timeout: Request timeout in seconds.

        Raises:
            ValueError: If API key is not provided and not found in environment.
        """
        self.api_key = api_key or os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Polygon.io API key not found. Please set POLYGON_API_KEY "
                "environment variable or pass api_key parameter."
            )

        self.base_url = self.BASE_URL
        self.timeout = timeout
        logger.info("MarketDataProvider initialized successfully")

    def get_stock_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get the latest stock quote for a given ticker symbol.

        This method retrieves the most recent trade price and related
        information for the specified stock ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA').

        Returns:
            Dict containing:
                - ticker (str): The ticker symbol
                - price (float): Latest trade price
                - timestamp (str): ISO format timestamp of the quote
                - volume (int): Trading volume
                - change (float): Price change from previous close
                - change_percent (float): Percentage change from previous close

        Raises:
            InvalidTickerError: If the ticker symbol is invalid or not found.
            APIConnectionError: If unable to connect to the API.
            RateLimitError: If API rate limit is exceeded.
            MarketDataError: For other API-related errors.

        Example:
            >>> provider = MarketDataProvider()
            >>> quote = provider.get_stock_quote("AAPL")
            >>> print(f"AAPL is trading at ${quote['price']}")
        """
        # Validate ticker input
        if not ticker or not isinstance(ticker, str):
            raise InvalidTickerError("Ticker must be a non-empty string")

        ticker = ticker.upper().strip()

        # Construct API endpoint - Using free-tier compatible endpoint
        # /v2/aggs/ticker/{ticker}/prev returns previous day's data (15-min delayed)
        endpoint = f"{self.base_url}/v2/aggs/ticker/{ticker}/prev"
        params = {"apiKey": self.api_key, "adjusted": "true"}

        try:
            logger.info(f"Fetching quote for ticker: {ticker}")

            # Make API request
            response = requests.get(endpoint, params=params, timeout=self.timeout)

            # Handle HTTP errors
            if response.status_code == 404:
                raise InvalidTickerError(
                    f"Ticker '{ticker}' not found. Please verify the symbol."
                )
            elif response.status_code == 429:
                raise RateLimitError("API rate limit exceeded. Please try again later.")
            elif response.status_code == 403:
                raise APIConnectionError(
                    "API authentication failed. Please check your API key."
                )

            response.raise_for_status()

            # Parse response
            data = response.json()

            # Validate response structure
            if data.get("status") != "OK":
                raise MarketDataError(
                    f"API returned non-OK status: {data.get('status')}"
                )

            results = data.get("results")
            if not results or len(results) == 0:
                raise MarketDataError("No price data found in API response")

            # Extract aggregate data for previous day
            agg_data = results[0]

            # Get close price as current price (most recent available)
            price = agg_data.get("c")
            if price is None:
                raise MarketDataError("Unable to extract price from API response")

            # Extract OHLCV data
            open_price = agg_data.get("o", 0)
            high_price = agg_data.get("h", 0)
            low_price = agg_data.get("l", 0)
            volume = agg_data.get("v", 0)

            # Calculate change (close - open for the day)
            change = price - open_price if open_price else 0
            change_percent = (change / open_price * 100) if open_price else 0

            # Get timestamp
            timestamp_ms = agg_data.get("t", 0)
            timestamp = (
                datetime.fromtimestamp(timestamp_ms / 1000).isoformat()
                if timestamp_ms
                else datetime.now().isoformat()
            )

            # Construct response
            quote_data = {
                "ticker": ticker,
                "price": round(price, 2),
                "timestamp": timestamp,
                "volume": volume,
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "previous_close": round(open_price, 2),
                "day_high": round(high_price, 2) if high_price else None,
                "day_low": round(low_price, 2) if low_price else None,
                "day_open": round(open_price, 2) if open_price else None,
            }

            logger.info(
                f"Successfully retrieved quote for {ticker}: ${quote_data['price']}"
            )

            return quote_data

        except Timeout:
            raise APIConnectionError(
                f"Request timed out after {self.timeout} seconds. "
                "Please check your connection and try again."
            )
        except HTTPError as e:
            raise APIConnectionError(f"HTTP error occurred: {str(e)}")
        except RequestException as e:
            raise APIConnectionError(f"Network error occurred: {str(e)}")
        except (KeyError, ValueError, TypeError) as e:
            raise MarketDataError(f"Error parsing API response: {str(e)}")

    def get_option_chain(
        self,
        ticker: str,
        expiration_date: Optional[str] = None,
        atm_strikes: Optional[int] = None,
        limit: int = 250,
    ) -> Dict[str, Any]:
        """
        Get the option chain for a given ticker symbol using yfinance.

        Uses yfinance (free, 15-min delayed data) to retrieve option contracts
        with pricing, volume, open interest, and Greeks. Much faster than Polygon.io
        snapshot calls and provides real data.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA').
            expiration_date: Optional expiration date filter (YYYY-MM-DD format).
                           If not provided, returns contracts for nearest expiration.
            atm_strikes: Optional filter for strikes around current price.
                        If provided, only returns contracts within range.
            limit: Maximum number of contracts to return (default: 250).

        Returns:
            Dict containing:
                - ticker (str): The underlying ticker symbol
                - stock_price (float): Current stock price
                - calls (List[Dict]): Call option contracts
                - puts (List[Dict]): Put option contracts
                - total_contracts (int): Total number of contracts returned
                - available_expirations (List[str]): Available expiration dates
                - note (str): Optional note about data source

        Raises:
            InvalidTickerError: If the ticker symbol is invalid or not found.
            MarketDataError: For other errors.

        Example:
            >>> provider = MarketDataProvider()
            >>> chain = provider.get_option_chain("AAPL")
            >>> print(f"Found {chain['total_contracts']} contracts")
        """
        # Validate ticker input
        if not ticker or not isinstance(ticker, str):
            raise InvalidTickerError("Ticker must be a non-empty string")

        ticker = ticker.upper().strip()

        try:
            logger.info(f"Fetching option chain for {ticker} using yfinance")

            # Get stock object and current price
            stock = yf.Ticker(ticker)

            # Get current stock price from Polygon.io (fast, works on free tier)
            try:
                stock_data = self.get_stock_quote(ticker)
                stock_price = stock_data["price"]
            except Exception:
                # Fallback to yfinance if Polygon.io fails
                try:
                    info = stock.info
                    stock_price = info.get("currentPrice") or info.get(
                        "regularMarketPrice", 0
                    )
                    if not stock_price:
                        raise MarketDataError(
                            f"Unable to retrieve stock price for {ticker}"
                        )
                except Exception as e:
                    raise MarketDataError(
                        f"Unable to retrieve stock price for {ticker}: {e}"
                    )

            # Get available expiration dates
            expirations = stock.options
            if not expirations:
                raise InvalidTickerError(
                    f"No options found for ticker '{ticker}'. "
                    "The ticker may not have listed options."
                )

            # Convert expiration dates to YYYY-MM-DD format
            available_expirations = list(expirations)

            # Select which expiration(s) to fetch
            if expiration_date:
                # Filter to specific expiration
                if expiration_date in available_expirations:
                    expirations_to_fetch = [expiration_date]
                else:
                    raise InvalidTickerError(
                        f"Expiration date {expiration_date} not available for {ticker}. "
                        f"Available: {', '.join(available_expirations[:5])}"
                    )
            else:
                # Fetch first 3 expirations for diversity
                expirations_to_fetch = available_expirations[:3]

            # Fetch option chains for selected expirations
            all_calls = []
            all_puts = []

            for exp_date in expirations_to_fetch:
                try:
                    opt_chain = stock.option_chain(exp_date)

                    # Helper function to safely convert values, handling NaN
                    import pandas as pd

                    def safe_float(val):
                        """Convert to float, return None if NaN or missing."""
                        if val is None or pd.isna(val):
                            return None
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return None

                    def safe_int(val):
                        """Convert to int, return None if NaN or missing."""
                        if val is None or pd.isna(val):
                            return None
                        try:
                            return int(val)
                        except (ValueError, TypeError):
                            return None

                    # Process calls
                    calls_df = opt_chain.calls
                    for _, row in calls_df.iterrows():
                        call_contract = {
                            "ticker": row.get("contractSymbol", ""),
                            "strike": float(row.get("strike", 0)),
                            "expiration_date": exp_date,
                            "option_type": "call",
                            "last_price": safe_float(row.get("lastPrice")),
                            "bid": safe_float(row.get("bid")),
                            "ask": safe_float(row.get("ask")),
                            "volume": safe_int(row.get("volume")),
                            "open_interest": safe_int(row.get("openInterest")),
                            "implied_volatility": safe_float(
                                row.get("impliedVolatility")
                            ),
                        }
                        all_calls.append(call_contract)

                    # Process puts
                    puts_df = opt_chain.puts
                    for _, row in puts_df.iterrows():
                        put_contract = {
                            "ticker": row.get("contractSymbol", ""),
                            "strike": float(row.get("strike", 0)),
                            "expiration_date": exp_date,
                            "option_type": "put",
                            "last_price": safe_float(row.get("lastPrice")),
                            "bid": safe_float(row.get("bid")),
                            "ask": safe_float(row.get("ask")),
                            "volume": safe_int(row.get("volume")),
                            "open_interest": safe_int(row.get("openInterest")),
                            "implied_volatility": safe_float(
                                row.get("impliedVolatility")
                            ),
                        }
                        all_puts.append(put_contract)

                except Exception as e:
                    logger.warning(
                        f"Failed to fetch options for {ticker} expiring {exp_date}: {e}"
                    )
                    continue

            # Combine all contracts
            all_contracts = all_calls + all_puts

            # Filter by ATM strikes if requested
            if atm_strikes and stock_price:
                filtered_calls = []
                filtered_puts = []

                for contract in all_calls:
                    strike = contract.get("strike")
                    if strike:
                        strike_diff_pct = abs(strike - stock_price) / stock_price * 100
                        if strike_diff_pct <= (atm_strikes * 3):
                            filtered_calls.append(contract)

                for contract in all_puts:
                    strike = contract.get("strike")
                    if strike:
                        strike_diff_pct = abs(strike - stock_price) / stock_price * 100
                        if strike_diff_pct <= (atm_strikes * 3):
                            filtered_puts.append(contract)

                all_calls = filtered_calls
                all_puts = filtered_puts
                all_contracts = all_calls + all_puts

                logger.info(
                    f"Filtered to {len(all_contracts)} contracts around ATM price ${stock_price}"
                )

            # Apply limit
            if len(all_contracts) > limit:
                # Distribute limit between calls and puts proportionally
                call_ratio = (
                    len(all_calls) / len(all_contracts) if all_contracts else 0.5
                )
                call_limit = int(limit * call_ratio)
                put_limit = limit - call_limit

                all_calls = all_calls[:call_limit]
                all_puts = all_puts[:put_limit]
                all_contracts = all_calls + all_puts

            result = {
                "ticker": ticker,
                "stock_price": stock_price,
                "calls": all_calls,
                "puts": all_puts,
                "contracts": all_contracts,
                "total_contracts": len(all_contracts),
                "available_expirations": available_expirations[:10],
                "note": "Data provided by yfinance (15-minute delayed). Free and unlimited!",
            }

            logger.info(
                f"Successfully retrieved {len(all_contracts)} option contracts "
                f"for {ticker} ({len(all_calls)} calls, {len(all_puts)} puts)"
            )

            return result

        except InvalidTickerError:
            raise
        except Exception as e:
            logger.error(f"Error fetching option chain for {ticker}: {e}")
            raise MarketDataError(f"Error fetching option chain for {ticker}: {str(e)}")

    def _get_option_snapshot(self, option_ticker: str) -> Dict[str, Any]:
        """
        Get snapshot data for a specific option contract.

        Note: This endpoint requires a paid Polygon.io subscription.
        Free tier users will receive contract metadata without pricing/Greeks.

        Args:
            option_ticker: The option contract ticker (e.g., 'O:AAPL250117C00150000')

        Returns:
            Dict containing snapshot data with pricing and Greeks (if available).
            Returns empty dict for free-tier users.

        Raises:
            MarketDataError: If unable to fetch snapshot data.
        """
        endpoint = f"{self.base_url}/v3/snapshot/options/{option_ticker}"
        params = {"apiKey": self.api_key}

        try:
            response = requests.get(endpoint, params=params, timeout=self.timeout)

            # Handle free tier limitation (403 Forbidden)
            if response.status_code == 403:
                logger.debug(
                    f"Options snapshot not available (requires paid plan): {option_ticker}"
                )
                return {}

            if response.status_code != 200:
                return {}

            data = response.json()

            # Check for NOT_AUTHORIZED status in response body
            if data.get("status") == "NOT_AUTHORIZED":
                logger.debug("Options pricing requires paid Polygon.io subscription")
                return {}

            results = data.get("results", {})

            # Extract relevant fields
            day_data = results.get("day", {})
            last_quote = results.get("last_quote", {})
            greeks = results.get("greeks", {})

            return {
                "last_price": results.get("last_trade", {}).get("price"),
                "bid": last_quote.get("bid"),
                "ask": last_quote.get("ask"),
                "volume": day_data.get("volume"),
                "open_interest": results.get("open_interest"),
                "implied_volatility": greeks.get("implied_volatility"),
                "delta": greeks.get("delta"),
                "gamma": greeks.get("gamma"),
                "theta": greeks.get("theta"),
                "vega": greeks.get("vega"),
            }

        except Exception as e:
            logger.debug(f"Failed to get snapshot for {option_ticker}: {e}")
            return {}

    def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """
        Get detailed information about a ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA').

        Returns:
            Dict containing:
                - ticker (str): The ticker symbol
                - name (str): Company name
                - market_cap (float): Market capitalization
                - sector (str): Industry sector
                - description (str): Company description

        Raises:
            InvalidTickerError: If the ticker symbol is invalid or not found.
            APIConnectionError: If unable to connect to the API.
            MarketDataError: For other API-related errors.
        """
        if not ticker or not isinstance(ticker, str):
            raise InvalidTickerError("Ticker must be a non-empty string")

        ticker = ticker.upper().strip()

        endpoint = f"{self.base_url}/v3/reference/tickers/{ticker}"
        params = {"apiKey": self.api_key}

        try:
            logger.info(f"Fetching ticker details for: {ticker}")

            response = requests.get(endpoint, params=params, timeout=self.timeout)

            if response.status_code == 404:
                raise InvalidTickerError(f"Ticker '{ticker}' not found")
            elif response.status_code == 429:
                raise RateLimitError("API rate limit exceeded")
            elif response.status_code == 403:
                raise APIConnectionError("API authentication failed")

            response.raise_for_status()

            data = response.json()

            if data.get("status") != "OK":
                raise MarketDataError(
                    f"API returned non-OK status: {data.get('status')}"
                )

            results = data.get("results", {})

            return {
                "ticker": ticker,
                "name": results.get("name", ""),
                "market_cap": results.get("market_cap", 0),
                "sector": results.get("sic_description", ""),
                "description": results.get("description", ""),
                "primary_exchange": results.get("primary_exchange", ""),
            }

        except Timeout:
            raise APIConnectionError(f"Request timed out after {self.timeout} seconds")
        except HTTPError as e:
            raise APIConnectionError(f"HTTP error occurred: {str(e)}")
        except RequestException as e:
            raise APIConnectionError(f"Network error occurred: {str(e)}")

    def get_stock_financials(self, ticker: str) -> Dict[str, Any]:
        """
        Get financial data for a ticker.

        Fetches key financial metrics including earnings, debt, equity, and growth rates.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA').

        Returns:
            Dict containing:
                - ticker (str): The ticker symbol
                - pe_ratio (float): Price-to-Earnings ratio
                - peg_ratio (float): PEG ratio
                - eps (float): Earnings per share
                - eps_growth (float): EPS growth rate (%)
                - revenue_growth (float): Revenue growth rate (%)
                - debt_to_equity (float): Debt-to-Equity ratio
                - current_ratio (float): Current ratio
                - market_cap (float): Market capitalization

        Raises:
            InvalidTickerError: If the ticker symbol is invalid or not found.
            APIConnectionError: If unable to connect to the API.
            MarketDataError: For other API-related errors.
        """
        if not ticker or not isinstance(ticker, str):
            raise InvalidTickerError("Ticker must be a non-empty string")

        ticker = ticker.upper().strip()

        # Get ticker details for market cap and basic info
        endpoint = f"{self.base_url}/vX/reference/financials"
        params = {
            "ticker": ticker,
            "limit": 4,  # Get last 4 quarters for growth calculations
            "apiKey": self.api_key,
        }

        try:
            logger.info(f"Fetching financials for: {ticker}")

            response = requests.get(  # type: ignore
                endpoint, params=params, timeout=self.timeout
            )

            if response.status_code == 404:
                raise InvalidTickerError(f"Financials not found for ticker '{ticker}'")
            elif response.status_code == 429:
                raise RateLimitError("API rate limit exceeded")
            elif response.status_code == 403:
                raise APIConnectionError("API authentication failed")

            response.raise_for_status()

            data = response.json()

            if data.get("status") != "OK":
                raise MarketDataError(
                    f"API returned non-OK status: {data.get('status')}"
                )

            results = data.get("results", [])

            if not results:
                logger.warning(f"No financial data found for {ticker}")
                return self._get_empty_financials(ticker)

            # Get most recent financial data
            latest = results[0] if results else {}
            financials = latest.get("financials", {})

            # Extract balance sheet data
            balance_sheet = financials.get("balance_sheet", {})
            current_assets = balance_sheet.get("current_assets", {}).get("value", 0)
            current_liabilities = balance_sheet.get("current_liabilities", {}).get(
                "value", 0
            )
            total_debt = balance_sheet.get("long_term_debt", {}).get("value", 0)
            total_equity = balance_sheet.get("equity", {}).get("value", 0)

            # Extract income statement data
            income_statement = financials.get("income_statement", {})
            net_income = income_statement.get("net_income_loss", {}).get("value", 0)
            revenues = income_statement.get("revenues", {}).get("value", 0)
            basic_eps = income_statement.get("basic_earnings_per_share", {}).get(
                "value", 0
            )

            # Calculate financial ratios
            current_ratio = (
                current_assets / current_liabilities
                if current_liabilities and current_liabilities != 0
                else 0
            )

            debt_to_equity = (
                total_debt / total_equity if total_equity and total_equity != 0 else 0
            )

            # Calculate growth rates (compare most recent to 4 quarters ago)
            eps_growth = 0.0
            revenue_growth = 0.0

            if len(results) >= 4:
                old_financials = results[3].get("financials", {})
                old_income = old_financials.get("income_statement", {})
                old_eps = old_income.get("basic_earnings_per_share", {}).get("value", 0)
                old_revenues = old_income.get("revenues", {}).get("value", 0)

                if old_eps and old_eps != 0:
                    eps_growth = ((basic_eps - old_eps) / abs(old_eps)) * 100

                if old_revenues and old_revenues != 0:
                    revenue_growth = (
                        (revenues - old_revenues) / abs(old_revenues)
                    ) * 100

            # Get current stock price for PE calculation
            try:
                quote = self.get_stock_quote(ticker)
                price = quote["price"]

                # Calculate PE ratio
                pe_ratio = price / basic_eps if basic_eps and basic_eps != 0 else 0

                # Calculate PEG ratio (PE / earnings growth rate)
                peg_ratio = (
                    pe_ratio / eps_growth if eps_growth and eps_growth > 0 else 0
                )

            except Exception as e:
                logger.warning(f"Failed to get stock price for {ticker}: {e}")
                price = 0
                pe_ratio = 0
                peg_ratio = 0

            # Get market cap from ticker details
            try:
                details = self.get_ticker_details(ticker)
                market_cap = (
                    details.get("market_cap", 0) / 1_000_000_000
                )  # Convert to billions
            except Exception:
                market_cap = 0

            result = {
                "ticker": ticker,
                "price": price,
                "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
                "peg_ratio": round(peg_ratio, 2) if peg_ratio else None,
                "eps": round(basic_eps, 2) if basic_eps else None,
                "eps_growth": round(eps_growth, 2) if eps_growth else None,
                "revenue_growth": round(revenue_growth, 2) if revenue_growth else None,
                "debt_to_equity": round(debt_to_equity, 2) if debt_to_equity else None,
                "current_ratio": round(current_ratio, 2) if current_ratio else None,
                "market_cap": round(market_cap, 2) if market_cap else None,
                "net_income": net_income,
                "revenues": revenues,
            }

            logger.info(f"Successfully retrieved financials for {ticker}")
            return result

        except Timeout:
            raise APIConnectionError(f"Request timed out after {self.timeout} seconds")
        except HTTPError as e:
            raise APIConnectionError(f"HTTP error occurred: {str(e)}")
        except RequestException as e:
            raise APIConnectionError(f"Network error occurred: {str(e)}")

    def _get_empty_financials(self, ticker: str) -> Dict[str, Any]:
        """
        Return empty financial data structure when no data is available.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with None values for all financial metrics
        """
        return {
            "ticker": ticker,
            "price": None,
            "pe_ratio": None,
            "peg_ratio": None,
            "eps": None,
            "eps_growth": None,
            "revenue_growth": None,
            "debt_to_equity": None,
            "current_ratio": None,
            "market_cap": None,
            "net_income": None,
            "revenues": None,
        }

    def get_stock_universe(self, universe_type: str = "popular") -> List[str]:
        """
        Get a list of stock tickers to screen.

        Returns a predefined universe of stocks based on the type specified.

        Args:
            universe_type: Type of stock universe to return. Options:
                - "popular": Popular large-cap stocks (default)
                - "sp500_sample": Sample of S&P 500 stocks
                - "tech": Technology sector stocks
                - "all": All available stocks (requires premium API tier)

        Returns:
            List of stock ticker symbols

        Example:
            >>> provider = MarketDataProvider()
            >>> tickers = provider.get_stock_universe("popular")
            >>> len(tickers)
            50
        """
        # Predefined stock universes for screening
        universes = {
            "popular": [
                # Technology
                "AAPL",
                "MSFT",
                "GOOGL",
                "META",
                "NVDA",
                "TSLA",
                "AMD",
                "INTC",
                "AVGO",
                "ADBE",
                "CRM",
                "ORCL",
                "CSCO",
                "QCOM",
                "NOW",
                "AMAT",
                # Finance
                "JPM",
                "BAC",
                "WFC",
                "GS",
                "MS",
                "C",
                "BLK",
                "SCHW",
                # Healthcare
                "JNJ",
                "UNH",
                "PFE",
                "ABBV",
                "TMO",
                "LLY",
                "MRK",
                "ABT",
                # Consumer
                "AMZN",
                "WMT",
                "HD",
                "MCD",
                "NKE",
                "SBUX",
                "TGT",
                "COST",
                # Industrial
                "BA",
                "CAT",
                "HON",
                "MMM",
                "GE",
                "RTX",
            ],
            "sp500_sample": [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "NVDA",
                "META",
                "TSLA",
                "BRK.B",
                "UNH",
                "XOM",
                "JNJ",
                "JPM",
                "V",
                "PG",
                "MA",
                "HD",
                "CVX",
                "LLY",
                "ABBV",
                "MRK",
                "PEP",
                "COST",
                "AVGO",
                "WMT",
                "ADBE",
                "CRM",
                "MCD",
                "CSCO",
                "ACN",
                "NFLX",
                "TMO",
                "ABT",
                "DHR",
                "NKE",
                "BAC",
                "DIS",
                "TXN",
                "VZ",
                "INTC",
                "PM",
                "UPS",
            ],
            "tech": [
                "AAPL",
                "MSFT",
                "GOOGL",
                "META",
                "NVDA",
                "TSLA",
                "AMD",
                "INTC",
                "AVGO",
                "ADBE",
                "CRM",
                "ORCL",
                "CSCO",
                "QCOM",
                "NOW",
                "AMAT",
                "NFLX",
                "UBER",
                "SNOW",
                "PLTR",
                "COIN",
                "SQ",
                "SHOP",
                "ZM",
                "TWLO",
                "CRWD",
                "NET",
                "DDOG",
                "MDB",
                "FTNT",
                "PANW",
            ],
        }

        if universe_type in universes:
            logger.info(
                f"Returning {universe_type} stock universe with "
                f"{len(universes[universe_type])} tickers"
            )
            return universes[universe_type]

        # Default to popular stocks
        logger.warning(
            f"Unknown universe type '{universe_type}', returning popular stocks"
        )
        return universes["popular"]

    def get_vix(self) -> Dict[str, Any]:
        """
        Get the current VIX (Volatility Index) value from Yahoo Finance.

        The VIX measures the market's expectation of 30-day forward-looking volatility.
        Values are returned as percentages.

        Returns:
            Dictionary containing VIX data:
            - value: Current VIX value
            - timestamp: When the data was retrieved

        Raises:
            MarketDataError: If unable to fetch VIX data

        Example:
            >>> provider = MarketDataProvider()
            >>> vix_data = provider.get_vix()
            >>> print(f"VIX: {vix_data['value']:.2f}")
        """
        try:
            logger.info("Fetching VIX data from yfinance")

            # Fetch VIX from Yahoo Finance (ticker: ^VIX)
            vix = yf.Ticker("^VIX")

            # Get the most recent price
            vix_info = vix.info

            # Try to get current price from various fields
            current_price = None
            if "regularMarketPrice" in vix_info:
                current_price = vix_info["regularMarketPrice"]
            elif "previousClose" in vix_info:
                current_price = vix_info["previousClose"]

            if current_price is None:
                # Fallback: get from history
                hist = vix.history(period="1d")
                if not hist.empty:
                    current_price = float(hist["Close"].iloc[-1])

            if current_price is None:
                raise MarketDataError("Unable to retrieve VIX value")

            result = {
                "value": float(current_price),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Successfully fetched VIX: {result['value']:.2f}")
            return result

        except Exception as e:
            logger.error(f"Error fetching VIX data: {str(e)}")
            raise MarketDataError(f"Failed to fetch VIX data: {str(e)}")

    def health_check(self) -> bool:
        """
        Check if the API connection is healthy.

        Returns:
            bool: True if API is accessible, False otherwise.
        """
        try:
            endpoint = f"{self.base_url}/v2/aggs/ticker/AAPL/prev"
            params = {"apiKey": self.api_key}

            response = requests.get(endpoint, params=params, timeout=self.timeout)

            return response.status_code == 200
        except RequestException:
            return False
