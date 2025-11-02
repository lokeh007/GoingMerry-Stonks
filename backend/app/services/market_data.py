"""
Market Data Service Module.

This module provides integration with Polygon.io API for real-time and
historical market data retrieval.
"""

import os
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging

import requests
from requests.exceptions import RequestException, Timeout, HTTPError


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

        # Construct API endpoint
        endpoint = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        params = {"apiKey": self.api_key}

        try:
            logger.info(f"Fetching quote for ticker: {ticker}")

            # Make API request
            response = requests.get(
                endpoint,
                params=params,
                timeout=self.timeout
            )

            # Handle HTTP errors
            if response.status_code == 404:
                raise InvalidTickerError(
                    f"Ticker '{ticker}' not found. Please verify the symbol."
                )
            elif response.status_code == 429:
                raise RateLimitError(
                    "API rate limit exceeded. Please try again later."
                )
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

            ticker_data = data.get("ticker")
            if not ticker_data:
                raise MarketDataError("No ticker data found in API response")

            # Extract quote information
            last_quote = ticker_data.get("lastQuote", {})
            last_trade = ticker_data.get("lastTrade", {})
            day_data = ticker_data.get("day", {})
            prev_day = ticker_data.get("prevDay", {})

            # Get the latest price (prefer last trade, fallback to last quote)
            price = last_trade.get("p") or last_quote.get("p")
            if price is None:
                raise MarketDataError("Unable to extract price from API response")

            # Calculate change from previous close
            prev_close = prev_day.get("c", 0)
            change = price - prev_close if prev_close else 0
            change_percent = (change / prev_close * 100) if prev_close else 0

            # Construct response
            quote_data = {
                "ticker": ticker,
                "price": round(price, 2),
                "timestamp": datetime.fromtimestamp(
                    last_trade.get("t", 0) / 1000
                ).isoformat() if last_trade.get("t") else datetime.now().isoformat(),
                "volume": day_data.get("v", 0),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "previous_close": prev_close,
                "day_high": day_data.get("h"),
                "day_low": day_data.get("l"),
                "day_open": day_data.get("o"),
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
            raise APIConnectionError(
                f"HTTP error occurred: {str(e)}"
            )
        except RequestException as e:
            raise APIConnectionError(
                f"Network error occurred: {str(e)}"
            )
        except (KeyError, ValueError, TypeError) as e:
            raise MarketDataError(
                f"Error parsing API response: {str(e)}"
            )

    def get_option_chain(
        self,
        ticker: str,
        expiration_date: Optional[str] = None,
        limit: int = 250
    ) -> Dict[str, Any]:
        """
        Get the option chain for a given ticker symbol.

        Retrieves available option contracts (both calls and puts) for the
        specified underlying stock ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA').
            expiration_date: Optional expiration date filter (YYYY-MM-DD format).
                           If not provided, returns contracts for all expirations.
            limit: Maximum number of contracts to return (default: 250, max: 1000).

        Returns:
            Dict containing:
                - ticker (str): The underlying ticker symbol
                - stock_price (float): Current stock price
                - contracts (List[Dict]): List of option contracts with details
                - total_contracts (int): Total number of contracts returned

        Raises:
            InvalidTickerError: If the ticker symbol is invalid or not found.
            APIConnectionError: If unable to connect to the API.
            RateLimitError: If API rate limit is exceeded.
            MarketDataError: For other API-related errors.

        Example:
            >>> provider = MarketDataProvider()
            >>> chain = provider.get_option_chain("AAPL")
            >>> print(f"Found {chain['total_contracts']} contracts")
        """
        # Validate ticker input
        if not ticker or not isinstance(ticker, str):
            raise InvalidTickerError("Ticker must be a non-empty string")

        ticker = ticker.upper().strip()

        # First, get the current stock price
        try:
            stock_data = self.get_stock_quote(ticker)
            stock_price = stock_data["price"]
        except Exception as e:
            logger.error(f"Failed to get stock price for {ticker}: {e}")
            raise

        # Construct options API endpoint
        endpoint = f"{self.base_url}/v3/reference/options/contracts"
        params = {
            "underlying_ticker": ticker,
            "limit": min(limit, 1000),  # API max is 1000
            "apiKey": self.api_key,
        }

        # Add expiration date filter if provided
        if expiration_date:
            params["expiration_date"] = expiration_date

        try:
            logger.info(f"Fetching option chain for ticker: {ticker}")

            # Make API request
            response = requests.get(
                endpoint,
                params=params,
                timeout=self.timeout
            )

            # Handle HTTP errors
            if response.status_code == 404:
                raise InvalidTickerError(
                    f"No options found for ticker '{ticker}'. "
                    "The ticker may not have listed options."
                )
            elif response.status_code == 429:
                raise RateLimitError(
                    "API rate limit exceeded. Please try again later."
                )
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

            contracts = data.get("results", [])

            # For each contract, get snapshot data for pricing info
            enriched_contracts = []
            for contract in contracts[:50]:  # Limit to avoid too many requests
                contract_ticker = contract.get("ticker")
                if not contract_ticker:
                    continue

                # Get contract snapshot for pricing data
                try:
                    snapshot = self._get_option_snapshot(contract_ticker)
                    enriched_contract = {
                        "ticker": contract_ticker,
                        "strike": contract.get("strike_price"),
                        "expiration_date": contract.get("expiration_date"),
                        "option_type": contract.get("contract_type", "").lower(),
                        "last_price": snapshot.get("last_price"),
                        "bid": snapshot.get("bid"),
                        "ask": snapshot.get("ask"),
                        "volume": snapshot.get("volume"),
                        "open_interest": snapshot.get("open_interest"),
                        "implied_volatility": snapshot.get("implied_volatility"),
                        "delta": snapshot.get("delta"),
                        "gamma": snapshot.get("gamma"),
                        "theta": snapshot.get("theta"),
                        "vega": snapshot.get("vega"),
                    }
                    enriched_contracts.append(enriched_contract)
                except Exception as e:
                    logger.warning(f"Failed to get snapshot for {contract_ticker}: {e}")
                    # Add contract with basic info even if snapshot fails
                    enriched_contracts.append({
                        "ticker": contract_ticker,
                        "strike": contract.get("strike_price"),
                        "expiration_date": contract.get("expiration_date"),
                        "option_type": contract.get("contract_type", "").lower(),
                    })

            # Separate into calls and puts
            calls = [c for c in enriched_contracts if c.get("option_type") == "call"]
            puts = [c for c in enriched_contracts if c.get("option_type") == "put"]

            result = {
                "ticker": ticker,
                "stock_price": stock_price,
                "calls": calls,
                "puts": puts,
                "contracts": enriched_contracts,
                "total_contracts": len(enriched_contracts),
            }

            logger.info(
                f"Successfully retrieved {len(enriched_contracts)} option contracts "
                f"for {ticker}"
            )

            return result

        except Timeout:
            raise APIConnectionError(
                f"Request timed out after {self.timeout} seconds. "
                "Please check your connection and try again."
            )
        except HTTPError as e:
            raise APIConnectionError(
                f"HTTP error occurred: {str(e)}"
            )
        except RequestException as e:
            raise APIConnectionError(
                f"Network error occurred: {str(e)}"
            )
        except (KeyError, ValueError, TypeError) as e:
            raise MarketDataError(
                f"Error parsing API response: {str(e)}"
            )

    def _get_option_snapshot(self, option_ticker: str) -> Dict[str, Any]:
        """
        Get snapshot data for a specific option contract.

        Args:
            option_ticker: The option contract ticker (e.g., 'O:AAPL250117C00150000')

        Returns:
            Dict containing snapshot data with pricing and Greeks.

        Raises:
            MarketDataError: If unable to fetch snapshot data.
        """
        endpoint = f"{self.base_url}/v3/snapshot/options/{option_ticker}"
        params = {"apiKey": self.api_key}

        try:
            response = requests.get(
                endpoint,
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                return {}

            data = response.json()
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

    def health_check(self) -> bool:
        """
        Check if the API connection is healthy.

        Returns:
            bool: True if API is accessible, False otherwise.
        """
        try:
            endpoint = f"{self.base_url}/v2/aggs/ticker/AAPL/prev"
            params = {"apiKey": self.api_key}

            response = requests.get(
                endpoint,
                params=params,
                timeout=self.timeout
            )

            return response.status_code == 200
        except RequestException:
            return False
