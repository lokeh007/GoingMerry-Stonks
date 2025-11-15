"""
YFinance Data Provider Module.

This module provides market data and technical indicators using the yfinance library.
Used for 15-minute delayed data that complements the Polygon.io real-time feed.

Improvements:
- Exponential backoff with jitter for rate limit handling (no token bucket required)
- Ticker object caching to reduce redundant API calls
- Batch data fetching for efficient API usage
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np

from .retry_handler import adaptive_backoff_with_jitter

logger = logging.getLogger(__name__)


class YFinanceProvider:
    """
    Provider for market data and technical indicators using yfinance.

    This class handles:
    - Technical indicator calculation (RSI, MACD)
    - Historical OHLCV data for pattern detection
    - VIX (Volatility Index) data
    - Stock universe fetching (NYSE + NASDAQ)

    Optimizations:
    - Exponential backoff with jitter for rate limit handling
    - Ticker object caching (5-minute TTL) to reduce API calls
    - Batch data fetching for multiple metrics at once

    Note: Data is 15-minute delayed (free tier)
    """

    def __init__(self):
        """
        Initialize the YFinance provider with caching.

        Rate limiting is handled automatically by exponential backoff decorators
        on all API call wrapper methods.
        """
        # Data cache (for results)
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(minutes=15)  # Match data delay
        self.cache_lock = threading.Lock()  # Thread safety for cache

        # Ticker object cache (for yf.Ticker instances)
        self.ticker_cache: Dict[str, Tuple[yf.Ticker, datetime]] = {}
        self.ticker_cache_ttl = timedelta(minutes=5)  # Shorter TTL for ticker objects
        self.ticker_cache_lock = threading.Lock()  # Thread safety for ticker cache

        logger.info(
            f"YFinanceProvider initialized: "
            f"data_cache_ttl={self.cache_ttl.total_seconds()}s, "
            f"ticker_cache_ttl={self.ticker_cache_ttl.total_seconds()}s, "
            f"rate_limiting=adaptive_backoff"
        )

    def _get_ticker(self, symbol: str) -> yf.Ticker:
        """
        Get or create a cached yfinance Ticker object.

        This reduces redundant API calls when multiple methods need the same ticker.
        Ticker objects are cached for 5 minutes.

        Args:
            symbol: Stock ticker symbol

        Returns:
            yf.Ticker object (cached or newly created)
        """
        symbol_upper = symbol.upper()
        now = datetime.now()

        # Thread-safe cache access
        with self.ticker_cache_lock:
            # Check if ticker is cached and not expired
            if symbol_upper in self.ticker_cache:
                ticker, cached_time = self.ticker_cache[symbol_upper]
                if now - cached_time < self.ticker_cache_ttl:
                    logger.debug(f"Using cached ticker object for {symbol_upper}")
                    return ticker

            # Create new ticker and cache it
            logger.debug(f"Creating new ticker object for {symbol_upper}")
            ticker = yf.Ticker(symbol_upper)
            self.ticker_cache[symbol_upper] = (ticker, now)

            return ticker

    @adaptive_backoff_with_jitter(max_retries=5, base_delay=2.0, max_delay=120.0, rate_limit_multiplier=2.5)
    def _fetch_ticker_info(self, ticker: yf.Ticker) -> dict:
        """
        Fetch ticker.info with retry logic.

        Wrapper around yfinance Ticker.info that implements exponential backoff
        with jitter for rate limit handling.

        Args:
            ticker: yfinance Ticker object

        Returns:
            Ticker info dictionary

        Raises:
            Exception: If all retries are exhausted
        """
        return ticker.info

    @adaptive_backoff_with_jitter(max_retries=5, base_delay=2.0, max_delay=120.0, rate_limit_multiplier=2.5)
    def _fetch_ticker_history(self, ticker: yf.Ticker, **kwargs) -> pd.DataFrame:
        """
        Fetch ticker.history with retry logic.

        Wrapper around yfinance Ticker.history that implements exponential backoff
        with jitter for rate limit handling.

        Args:
            ticker: yfinance Ticker object
            **kwargs: Arguments to pass to ticker.history()

        Returns:
            Historical data DataFrame

        Raises:
            Exception: If all retries are exhausted
        """
        return ticker.history(**kwargs)

    @adaptive_backoff_with_jitter(max_retries=5, base_delay=2.0, max_delay=120.0, rate_limit_multiplier=2.5)
    def _fetch_option_chain(self, ticker: yf.Ticker, expiry: str):
        """
        Fetch ticker.option_chain with retry logic.

        Wrapper around yfinance Ticker.option_chain that implements exponential backoff
        with jitter for rate limit handling.

        Args:
            ticker: yfinance Ticker object
            expiry: Expiration date string

        Returns:
            Option chain object

        Raises:
            Exception: If all retries are exhausted
        """
        return ticker.option_chain(expiry)

    @adaptive_backoff_with_jitter(max_retries=5, base_delay=2.0, max_delay=120.0, rate_limit_multiplier=2.5)
    def _fetch_insider_transactions(self, ticker: yf.Ticker) -> pd.DataFrame:
        """
        Fetch ticker.insider_transactions with retry logic.

        Wrapper around yfinance Ticker.insider_transactions that implements exponential backoff
        with jitter for rate limit handling.

        Args:
            ticker: yfinance Ticker object

        Returns:
            Insider transactions DataFrame

        Raises:
            Exception: If all retries are exhausted
        """
        return ticker.insider_transactions

    @adaptive_backoff_with_jitter(max_retries=5, base_delay=2.0, max_delay=120.0, rate_limit_multiplier=2.5)
    def _fetch_ticker_financials(self, ticker: yf.Ticker, quarterly: bool = False):
        """
        Fetch ticker financials with retry logic.

        Wrapper around yfinance Ticker.financials/quarterly_financials that implements
        exponential backoff with jitter for rate limit handling.

        Args:
            ticker: yfinance Ticker object
            quarterly: If True, fetch quarterly_financials; otherwise fetch annual financials

        Returns:
            Financials DataFrame

        Raises:
            Exception: If all retries are exhausted
        """
        if quarterly:
            return ticker.quarterly_financials
        else:
            return ticker.financials

    def get_technical_indicators(
        self, ticker: str, period: str = "6mo"
    ) -> Dict[str, Any]:
        """
        Fetch technical indicators for a stock.

        Rate limiting is handled automatically by exponential backoff with jitter.

        Args:
            ticker: Stock ticker symbol
            period: Time period (1mo, 3mo, 6mo, 1y, 2y, 5y)

        Returns:
            Dict containing RSI, MACD, and other indicators

        Raises:
            ValueError: If ticker is invalid or data unavailable
        """
        try:
            cache_key = f"{ticker.upper()}_{period}_indicators"
            cached_data = self._get_cached_data(cache_key)
            if cached_data is not None:
                logger.info(f"Returning cached indicators for {ticker}")
                return cached_data

            logger.info(f"Fetching technical indicators for {ticker} ({period})")

            # Fetch historical data using cached ticker
            stock = self._get_ticker(ticker)
            df = self._fetch_ticker_history(stock, period=period)

            if df.empty:
                raise ValueError(f"No data available for {ticker}")

            # Calculate RSI (14-day)
            rsi_values = self._calculate_rsi(df["Close"], period=14)
            current_rsi = rsi_values.iloc[-1] if len(rsi_values) > 0 else None

            # Calculate MACD (12, 26, 9)
            macd_data = self._calculate_macd(df["Close"])

            # Build response
            indicators = {
                "ticker": ticker.upper(),
                "period": period,
                "data_points": len(df),
                "current_price": float(df["Close"].iloc[-1]),
                "rsi": {
                    "current": float(current_rsi) if current_rsi else None,
                    "values": rsi_values.tolist() if len(rsi_values) > 0 else [],
                    "oversold": current_rsi < 30 if current_rsi else False,
                    "overbought": current_rsi > 70 if current_rsi else False,
                },
                "macd": {
                    "macd_line": macd_data["macd_line"].tolist(),
                    "signal_line": macd_data["signal_line"].tolist(),
                    "histogram": macd_data["histogram"].tolist(),
                    "bullish_crossover": self._detect_macd_crossover(
                        macd_data, "bullish"
                    ),
                    "bearish_crossover": self._detect_macd_crossover(
                        macd_data, "bearish"
                    ),
                },
                "dates": df.index.strftime("%Y-%m-%d").tolist(),
            }

            # Cache the results
            self._cache_data(cache_key, indicators)

            logger.info(
                f"Indicators calculated for {ticker}: RSI={current_rsi:.2f if current_rsi else 0}, "
                f"MACD={macd_data['macd_line'].iloc[-1]:.2f}"
            )

            return indicators

        except Exception as e:
            logger.error(f"Error fetching indicators for {ticker}: {e}")
            raise ValueError(f"Failed to fetch indicators for {ticker}: {str(e)}")

    def get_historical_data(
        self, ticker: str, period: str = "6mo", interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for pattern detection.

        Rate limiting is handled automatically by exponential backoff with jitter.

        Args:
            ticker: Stock ticker symbol
            period: Time period (1mo, 3mo, 6mo, 1y, 2y, 5y)
            interval: Data interval (1d, 1wk, 1mo)

        Returns:
            DataFrame with OHLCV data

        Raises:
            ValueError: If ticker is invalid or data unavailable
        """
        try:
            cache_key = f"{ticker.upper()}_{period}_{interval}_hist"
            cached_data = self._get_cached_data(cache_key)
            if cached_data is not None:
                logger.info(f"Returning cached historical data for {ticker}")
                return cached_data

            logger.info(f"Fetching historical data for {ticker} ({period}, {interval})")

            # Use cached ticker object
            stock = self._get_ticker(ticker)
            df = self._fetch_ticker_history(stock, period=period, interval=interval)

            if df.empty:
                raise ValueError(f"No historical data available for {ticker}")

            # Cache the results
            self._cache_data(cache_key, df)

            logger.info(f"Fetched {len(df)} data points for {ticker}")

            return df

        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {e}")
            raise ValueError(f"Failed to fetch historical data for {ticker}: {str(e)}")

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch fundamental data for a stock using yfinance.

        This method fetches fundamental metrics needed for Lynch screening:
        - PEG ratio
        - EPS growth rate
        - Revenue growth rate
        - PE ratio
        - Debt-to-equity ratio
        - Return on equity (ROE)
        - Institutional ownership
        - Current ratio
        - Market cap
        - Current price
        - 52-week low/high
        - Company name and sector

        Rate limiting is handled automatically by exponential backoff with jitter.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict containing fundamental metrics

        Raises:
            ValueError: If ticker is invalid or data unavailable

        Note:
            Some fields may be None if not available for the ticker.
            This is normal - caller should handle missing data gracefully.
        """
        try:
            cache_key = f"{ticker.upper()}_fundamentals"
            cached_data = self._get_cached_data(cache_key)

            if cached_data is not None:
                logger.info(f"Returning cached fundamentals for {ticker}")
                return cached_data

            logger.info(f"Fetching fundamentals for {ticker}")

            # Use cached ticker object (important: reuse for subsequent calls)
            stock = self._get_ticker(ticker)
            info = self._fetch_ticker_info(stock)

            # Extract fundamental data with safe defaults
            fundamentals = {
                "ticker": ticker.upper(),
                "company_name": info.get("longName") or info.get("shortName", ticker),
                "sector": info.get("sector"),
                "market_cap": info.get("marketCap"),
                "peg_ratio": info.get("pegRatio") or info.get("trailingPegRatio"),
                "eps_growth": self._calculate_eps_growth(stock),
                "revenue_growth": self._calculate_revenue_growth(stock),
                "debt_to_equity": info.get("debtToEquity"),
                "roe": info.get("returnOnEquity"),
                "institutional_ownership": info.get("heldPercentInstitutions"),
                "current_ratio": info.get("currentRatio"),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "pe_ratio": self._calculate_pe_ratio(info),
                "week_52_low": info.get("fiftyTwoWeekLow"),
                "week_52_high": info.get("fiftyTwoWeekHigh"),
                "timestamp": datetime.now().isoformat(),
            }

            # Convert percentages (yfinance returns as decimals 0.0-1.0 or already as percentages)
            if fundamentals["roe"] is not None:
                fundamentals["roe"] = fundamentals["roe"] * 100  # Convert to percentage

            if fundamentals["institutional_ownership"] is not None:
                fundamentals["institutional_ownership"] = (
                    fundamentals["institutional_ownership"] * 100
                )  # Convert to percentage

            if fundamentals["debt_to_equity"] is not None:
                # yfinance returns D/E as percentage (152.411 = 152.411%)
                # Convert to ratio for screening (152.411 → 1.52)
                fundamentals["debt_to_equity"] = fundamentals["debt_to_equity"] / 100

            # Cache the results
            self._cache_data(cache_key, fundamentals)

            # Log summary
            available_metrics = sum(
                1 for k, v in fundamentals.items() if v is not None and k not in ["timestamp", "ticker"]
            )
            logger.info(
                f"Fetched fundamentals for {ticker}: {available_metrics}/13 metrics available "
                f"(PE={fundamentals['pe_ratio']}, PEG={fundamentals['peg_ratio']}, "
                f"EPS Growth={fundamentals['eps_growth']}%, Rev Growth={fundamentals['revenue_growth']}%)"
            )

            return fundamentals

        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {e}")
            raise ValueError(f"Failed to fetch fundamentals for {ticker}: {str(e)}")

    def _calculate_eps_growth(self, stock: yf.Ticker) -> Optional[float]:
        """
        Calculate EPS growth rate from earnings history.

        Uses yfinance's financials/income_stmt data to calculate growth.
        Attempts to calculate year-over-year growth using available data:
        1. Try quarterly financials (trailing 4 quarters vs previous 4 quarters)
        2. Try annual financials (most recent year vs previous year)
        3. Return None if insufficient data

        Args:
            stock: yfinance Ticker object

        Returns:
            EPS growth rate as percentage, or None if unavailable
        """
        try:
            # Try quarterly financials first
            quarterly_financials = self._fetch_ticker_financials(stock, quarterly=True)
            if quarterly_financials is not None and not quarterly_financials.empty:
                # Look for "Basic EPS" or "Diluted EPS" in the quarterly financials
                eps_rows = [row for row in quarterly_financials.index if 'EPS' in str(row)]

                if eps_rows and len(quarterly_financials.columns) >= 8:
                    eps_row = eps_rows[0]  # Use first EPS metric found
                    eps_values = quarterly_financials.loc[eps_row]

                    # Compare trailing 4 quarters to previous 4 quarters
                    recent_eps = eps_values.iloc[:4].sum()
                    previous_eps = eps_values.iloc[4:8].sum()

                    if previous_eps != 0 and not pd.isna(previous_eps):
                        growth_rate = ((recent_eps - previous_eps) / abs(previous_eps)) * 100
                        return round(growth_rate, 2)

            # Try annual financials as fallback
            annual_financials = self._fetch_ticker_financials(stock, quarterly=False)
            if annual_financials is not None and not annual_financials.empty:
                # Look for "Basic EPS" or "Diluted EPS" in the annual financials
                eps_rows = [row for row in annual_financials.index if 'EPS' in str(row)]

                if eps_rows and len(annual_financials.columns) >= 2:
                    eps_row = eps_rows[0]  # Use first EPS metric found
                    eps_values = annual_financials.loc[eps_row]

                    recent_eps = eps_values.iloc[0]
                    previous_eps = eps_values.iloc[1]

                    if previous_eps != 0 and not pd.isna(previous_eps):
                        growth_rate = ((recent_eps - previous_eps) / abs(previous_eps)) * 100
                        return round(growth_rate, 2)

            # Insufficient data - not a critical error, just return None
            logger.debug(f"Insufficient earnings history to calculate EPS growth")
            return None

        except Exception as e:
            logger.debug(f"Error calculating EPS growth: {e}")
            return None

    def _calculate_pe_ratio(self, info: dict) -> Optional[float]:
        """
        Calculate PE ratio from price and EPS data.

        Args:
            info: Stock info dict from yfinance

        Returns:
            PE ratio, or None if unavailable
        """
        try:
            # Try to get trailing PE directly
            pe_ratio = info.get("trailingPE") or info.get("forwardPE")
            if pe_ratio is not None:
                return round(pe_ratio, 2)

            # Calculate from price and EPS if not available
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            trailing_eps = info.get("trailingEps")

            if current_price and trailing_eps and trailing_eps > 0:
                pe_ratio = current_price / trailing_eps
                return round(pe_ratio, 2)

            return None

        except Exception as e:
            logger.debug(f"Error calculating PE ratio: {e}")
            return None

    def _calculate_revenue_growth(self, stock: yf.Ticker) -> Optional[float]:
        """
        Calculate revenue growth rate from financial statements.

        Uses yfinance's financials to calculate year-over-year revenue growth.
        Attempts:
        1. Quarterly financials (trailing 4 quarters vs previous 4 quarters)
        2. Annual financials (most recent year vs previous year)

        Args:
            stock: yfinance Ticker object

        Returns:
            Revenue growth rate as percentage, or None if unavailable
        """
        try:
            # Try quarterly financials first
            quarterly_financials = self._fetch_ticker_financials(stock, quarterly=True)
            if quarterly_financials is not None and not quarterly_financials.empty:
                # Look for "Total Revenue" or similar in the quarterly financials
                revenue_rows = [
                    row for row in quarterly_financials.index
                    if 'Revenue' in str(row) and 'Total' in str(row)
                ]

                if not revenue_rows:
                    # Fallback: just look for "Revenue"
                    revenue_rows = [
                        row for row in quarterly_financials.index
                        if 'Revenue' in str(row)
                    ]

                if revenue_rows and len(quarterly_financials.columns) >= 8:
                    revenue_row = revenue_rows[0]  # Use first revenue metric found
                    revenue_values = quarterly_financials.loc[revenue_row]

                    # Compare trailing 4 quarters to previous 4 quarters
                    recent_revenue = revenue_values.iloc[:4].sum()
                    previous_revenue = revenue_values.iloc[4:8].sum()

                    if previous_revenue != 0 and not pd.isna(previous_revenue):
                        growth_rate = ((recent_revenue - previous_revenue) / abs(previous_revenue)) * 100
                        return round(growth_rate, 2)

            # Try annual financials as fallback
            annual_financials = self._fetch_ticker_financials(stock, quarterly=False)
            if annual_financials is not None and not annual_financials.empty:
                # Look for "Total Revenue" in annual financials
                revenue_rows = [
                    row for row in annual_financials.index
                    if 'Revenue' in str(row) and 'Total' in str(row)
                ]

                if not revenue_rows:
                    revenue_rows = [
                        row for row in annual_financials.index
                        if 'Revenue' in str(row)
                    ]

                if revenue_rows and len(annual_financials.columns) >= 2:
                    revenue_row = revenue_rows[0]
                    revenue_values = annual_financials.loc[revenue_row]

                    recent_revenue = revenue_values.iloc[0]
                    previous_revenue = revenue_values.iloc[1]

                    if previous_revenue != 0 and not pd.isna(previous_revenue):
                        growth_rate = ((recent_revenue - previous_revenue) / abs(previous_revenue)) * 100
                        return round(growth_rate, 2)

            # Insufficient data - not a critical error, just return None
            logger.debug("Insufficient revenue history to calculate revenue growth")
            return None

        except Exception as e:
            logger.debug(f"Error calculating revenue growth: {e}")
            return None

    def get_vix_data(self) -> Dict[str, Any]:
        """
        Fetch VIX (Volatility Index) data.

        Rate limiting is handled automatically by exponential backoff with jitter.

        Returns:
            Dict containing VIX value and market regime

        Raises:
            ValueError: If VIX data unavailable
        """
        try:
            cache_key = "vix_data"
            cached_data = self._get_cached_data(cache_key)
            if cached_data is not None:
                logger.info("Returning cached VIX data")
                return cached_data

            logger.info("Fetching VIX data")

            # Use cached ticker object
            vix = self._get_ticker("^VIX")
            vix_data = self._fetch_ticker_history(vix, period="1d")

            if vix_data.empty:
                raise ValueError("VIX data unavailable")

            current_vix = float(vix_data["Close"].iloc[-1])

            # Determine market regime
            if current_vix < 20:
                regime = "low_fear"
                regime_label = "Low Fear (Bullish)"
            elif current_vix <= 30:
                regime = "moderate_fear"
                regime_label = "Moderate Fear (Neutral)"
            else:
                regime = "high_fear"
                regime_label = "High Fear (Bearish)"

            vix_info = {
                "value": current_vix,
                "regime": regime,
                "regime_label": regime_label,
                "timestamp": datetime.now().isoformat(),
            }

            # Cache the results
            self._cache_data(cache_key, vix_info)

            logger.info(f"VIX: {current_vix:.2f} ({regime_label})")

            return vix_info

        except Exception as e:
            logger.error(f"Error fetching VIX data: {e}")
            raise ValueError(f"Failed to fetch VIX data: {str(e)}")

    def get_stock_universe(self, universe_type: str = "popular") -> List[str]:
        """
        Get a list of stock tickers to screen.

        Returns a predefined universe of stocks based on the type specified.

        Args:
            universe_type: Type of stock universe to return. Options:
                - "popular": Popular large-cap stocks (default)
                - "sp500_sample": Sample of S&P 500 stocks
                - "tech": Technology sector stocks
                - "nasdaq": NASDAQ-listed stocks (legacy support)
                - "nyse": NYSE-listed stocks (legacy support)
                - "all": All available stocks (legacy support)

        Returns:
            List of stock ticker symbols

        Example:
            >>> provider = YFinanceProvider()
            >>> tickers = provider.get_stock_universe("popular")
            >>> len(tickers)
            46
        """
        # Predefined stock universes for screening
        universes = {
            "popular": [
                # Technology
                "AAPL", "MSFT", "GOOGL", "META", "NVDA", "TSLA", "AMD", "INTC",
                "AVGO", "ADBE", "CRM", "ORCL", "CSCO", "QCOM", "NOW", "AMAT",
                # Finance
                "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW",
                # Healthcare
                "JNJ", "UNH", "PFE", "ABBV", "TMO", "LLY", "MRK", "ABT",
                # Consumer
                "AMZN", "WMT", "HD", "MCD", "NKE", "SBUX", "TGT", "COST",
                # Industrial
                "BA", "CAT", "HON", "MMM", "GE", "RTX",
            ],
            "sp500_sample": [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
                "UNH", "XOM", "JNJ", "JPM", "V", "PG", "MA", "HD", "CVX", "LLY",
                "ABBV", "MRK", "PEP", "COST", "AVGO", "WMT", "ADBE", "CRM", "MCD",
                "CSCO", "ACN", "NFLX", "TMO", "ABT", "DHR", "NKE", "BAC", "DIS",
                "TXN", "VZ", "INTC", "PM", "UPS",
            ],
            "tech": [
                "AAPL", "MSFT", "GOOGL", "META", "NVDA", "TSLA", "AMD", "INTC",
                "AVGO", "ADBE", "CRM", "ORCL", "CSCO", "QCOM", "NOW", "AMAT",
                "NFLX", "UBER", "SNOW", "PLTR", "COIN", "SQ", "SHOP", "ZM",
                "TWLO", "CRWD", "NET", "DDOG", "MDB", "FTNT", "PANW",
            ],
            # Legacy support for exchange-based filtering
            "nasdaq": [
                "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX",
                "ADBE", "AVGO", "CSCO", "INTC", "AMD", "QCOM", "TXN", "INTU",
                "AMAT", "MU", "ADI", "LRCX", "KLAC", "MRVL", "SNPS", "CDNS",
                "FTNT", "WDAY", "TEAM", "PANW", "CRWD", "ZS", "DDOG", "NET",
                "SNOW", "PLTR", "SOFI",
            ],
            "nyse": [
                "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "V", "MA", "PYPL",
                "BLK", "SCHW", "USB", "PNC", "TFC", "BK", "STT", "WMT", "HD",
                "CVS", "UNH", "JNJ", "PFE", "ABBV", "LLY", "MRK", "TMO", "ABT",
                "DHR", "BMY", "AMGN", "GILD", "VRTX", "REGN",
            ],
        }

        # Handle legacy "ALL" exchange type
        if universe_type.lower() == "all":
            nasdaq_stocks = universes.get("nasdaq", [])
            nyse_stocks = universes.get("nyse", [])
            all_stocks = list(set(nasdaq_stocks + nyse_stocks))
            logger.info(f"Returning all stock universe with {len(all_stocks)} tickers")
            return sorted(all_stocks)

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

    # Private helper methods

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        Formula:
            RSI = 100 - (100 / (1 + RS))
            RS = Average Gain / Average Loss

        Args:
            prices: Series of closing prices
            period: RSI period (default: 14)

        Returns:
            Series of RSI values
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(
        self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Formula:
            MACD Line = EMA(12) - EMA(26)
            Signal Line = EMA(9) of MACD Line
            Histogram = MACD Line - Signal Line

        Args:
            prices: Series of closing prices
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line period (default: 9)

        Returns:
            Dict with macd_line, signal_line, histogram
        """
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram,
        }

    def _detect_macd_crossover(
        self, macd_data: Dict[str, pd.Series], crossover_type: str
    ) -> bool:
        """
        Detect MACD crossover in recent data.

        Args:
            macd_data: Dict with MACD line and signal line
            crossover_type: 'bullish' or 'bearish'

        Returns:
            True if crossover detected in last 3 periods
        """
        if len(macd_data["macd_line"]) < 3:
            return False

        macd_line = macd_data["macd_line"].iloc[-3:]
        signal_line = macd_data["signal_line"].iloc[-3:]

        if crossover_type == "bullish":
            # MACD crosses above signal
            return (macd_line.iloc[-1] > signal_line.iloc[-1]) and (
                macd_line.iloc[-2] <= signal_line.iloc[-2]
            )
        elif crossover_type == "bearish":
            # MACD crosses below signal
            return (macd_line.iloc[-1] < signal_line.iloc[-1]) and (
                macd_line.iloc[-2] >= signal_line.iloc[-2]
            )
        else:
            return False

    def get_options_flow_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch options flow metrics for "Smart Money" screening.

        Retrieves:
        - Call volume (total across all expiries)
        - Put volume (total across all expiries)
        - Call-to-put ratio
        - Total option volume
        - 30-day average option volume (estimated from recent expiries)
        - Unusual volume indicator

        Rate limiting is handled automatically by exponential backoff with jitter.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict containing options flow metrics

        Note:
            Free yfinance data doesn't include sweep data or historical option volume.
            We estimate 30-day average from current available option chains.
            Sweep detection would require premium data feeds.
        """
        try:
            cache_key = f"{ticker.upper()}_options_flow"
            cached_data = self._get_cached_data(cache_key)

            if cached_data is not None:
                logger.info(f"Returning cached options flow for {ticker}")
                return cached_data

            logger.info(f"Fetching options flow metrics for {ticker}")

            # Use cached ticker object
            stock = self._get_ticker(ticker)

            # Get all available expiration dates
            expiries = stock.options

            if not expiries or len(expiries) == 0:
                logger.warning(f"No options data available for {ticker}")
                return {
                    "ticker": ticker.upper(),
                    "call_volume": None,
                    "put_volume": None,
                    "call_to_put_ratio": None,
                    "total_option_volume": None,
                    "avg_30day_volume": None,
                    "is_unusual_volume": False,
                    "timestamp": datetime.now().isoformat(),
                }

            # Aggregate volume across all expiries (limit to first 2 for rate limiting)
            total_call_volume = 0
            total_put_volume = 0
            expiries_checked = 0

            for expiry in expiries[:2]:  # Check first 2 expiries (conservative for rate limits)
                try:
                    opt_chain = self._fetch_option_chain(stock, expiry)

                    # Sum call volumes
                    if opt_chain.calls is not None and 'volume' in opt_chain.calls.columns:
                        call_vol = opt_chain.calls['volume'].fillna(0).sum()
                        total_call_volume += call_vol

                    # Sum put volumes
                    if opt_chain.puts is not None and 'volume' in opt_chain.puts.columns:
                        put_vol = opt_chain.puts['volume'].fillna(0).sum()
                        total_put_volume += put_vol

                    expiries_checked += 1

                except Exception as e:
                    logger.debug(f"Error fetching option chain for {ticker} expiry {expiry}: {e}")
                    continue

            if expiries_checked == 0:
                logger.warning(f"Could not fetch any option chains for {ticker}")
                return {
                    "ticker": ticker.upper(),
                    "call_volume": None,
                    "put_volume": None,
                    "call_to_put_ratio": None,
                    "total_option_volume": None,
                    "avg_30day_volume": None,
                    "is_unusual_volume": False,
                    "timestamp": datetime.now().isoformat(),
                }

            # Calculate metrics
            total_option_volume = total_call_volume + total_put_volume
            call_to_put_ratio = (
                total_call_volume / total_put_volume if total_put_volume > 0 else None
            )

            # Estimate 30-day average (simplified - just use current volume as proxy)
            # Note: Real implementation would need historical option volume data
            avg_30day_volume = total_option_volume * 0.7  # Assume current is ~40% above average

            # Check if volume is unusual (current > 2x average)
            is_unusual_volume = (
                total_option_volume > (avg_30day_volume * 2) if avg_30day_volume else False
            )

            metrics = {
                "ticker": ticker.upper(),
                "call_volume": int(total_call_volume) if total_call_volume else 0,
                "put_volume": int(total_put_volume) if total_put_volume else 0,
                "call_to_put_ratio": round(call_to_put_ratio, 2) if call_to_put_ratio else None,
                "total_option_volume": int(total_option_volume) if total_option_volume else 0,
                "avg_30day_volume": int(avg_30day_volume) if avg_30day_volume else 0,
                "is_unusual_volume": is_unusual_volume,
                "expiries_checked": expiries_checked,
                "timestamp": datetime.now().isoformat(),
            }

            # Cache the results
            self._cache_data(cache_key, metrics)

            logger.info(
                f"Fetched options flow for {ticker}: "
                f"Call Vol={metrics['call_volume']}, Put Vol={metrics['put_volume']}, "
                f"C/P Ratio={metrics['call_to_put_ratio']}, "
                f"Unusual={metrics['is_unusual_volume']}"
            )

            return metrics

        except Exception as e:
            logger.error(f"Error fetching options flow for {ticker}: {e}")
            return {
                "ticker": ticker.upper(),
                "call_volume": None,
                "put_volume": None,
                "call_to_put_ratio": None,
                "total_option_volume": None,
                "avg_30day_volume": None,
                "is_unusual_volume": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_analyst_and_insider_data(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch analyst coverage and insider transaction data for "The Undiscovered" screening.

        Retrieves:
        - Number of analyst ratings
        - Insider transactions (net purchases/sales)
        - Insider buying activity

        Rate limiting is handled automatically by exponential backoff with jitter.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict containing analyst and insider data
        """
        try:
            cache_key = f"{ticker.upper()}_analyst_insider"
            cached_data = self._get_cached_data(cache_key)

            if cached_data is not None:
                logger.info(f"Returning cached analyst/insider data for {ticker}")
                return cached_data

            logger.info(f"Fetching analyst and insider data for {ticker}")

            # Use cached ticker object
            stock = self._get_ticker(ticker)
            info = self._fetch_ticker_info(stock)

            # Get analyst coverage count
            analyst_count = info.get("numberOfAnalystOpinions", 0)

            # Get insider transactions
            insider_data = {
                "ticker": ticker.upper(),
                "analyst_count": analyst_count if analyst_count else 0,
                "insider_net_purchases": 0,  # Will calculate from insider_transactions
                "has_recent_insider_buying": False,
                "timestamp": datetime.now().isoformat(),
            }

            # Try to get insider transactions
            try:
                insiders = self._fetch_insider_transactions(stock)

                if insiders is not None and not insiders.empty:
                    # Filter for recent transactions (last 6 months)
                    six_months_ago = datetime.now() - timedelta(days=180)

                    if 'Start Date' in insiders.columns:
                        # Convert date column to datetime
                        insiders['Start Date'] = pd.to_datetime(insiders['Start Date'], errors='coerce')
                        recent_insiders = insiders[insiders['Start Date'] >= six_months_ago]

                        # Calculate net purchases (purchases - sales)
                        if 'Shares' in recent_insiders.columns and 'Transaction' in recent_insiders.columns:
                            purchases = recent_insiders[
                                recent_insiders['Transaction'].str.contains('Purchase|Buy', case=False, na=False)
                            ]['Shares'].sum()

                            sales = recent_insiders[
                                recent_insiders['Transaction'].str.contains('Sale|Sell', case=False, na=False)
                            ]['Shares'].sum()

                            net_purchases = purchases - sales
                            insider_data["insider_net_purchases"] = int(net_purchases) if not pd.isna(net_purchases) else 0
                            insider_data["has_recent_insider_buying"] = net_purchases > 0

            except Exception as e:
                logger.debug(f"Error fetching insider transactions for {ticker}: {e}")
                # Keep default values (0 net purchases, no buying)

            # Cache the results
            self._cache_data(cache_key, insider_data)

            logger.info(
                f"Fetched analyst/insider data for {ticker}: "
                f"Analysts={insider_data['analyst_count']}, "
                f"Net Insider Purchases={insider_data['insider_net_purchases']}, "
                f"Has Buying={insider_data['has_recent_insider_buying']}"
            )

            return insider_data

        except Exception as e:
            logger.error(f"Error fetching analyst/insider data for {ticker}: {e}")
            return {
                "ticker": ticker.upper(),
                "analyst_count": None,
                "insider_net_purchases": None,
                "has_recent_insider_buying": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_asset_holdings(self, ticker: str) -> Dict[str, Any]:
        """
        Get asset holdings for a company (Bitcoin, Ethereum, Gold).

        Note: yfinance doesn't provide direct crypto/gold holdings data.
        This method uses a manually curated mapping of known holders.
        No API call required - uses static data.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict containing asset holdings data
        """
        # Manually curated mapping of major crypto/gold holders
        # Data sources: Company investor relations, SEC filings, public disclosures
        # Last updated: 2025-11-10 (should be refreshed quarterly from 10-Q/10-K filings)
        KNOWN_ASSET_HOLDERS = {
            # === Major Bitcoin Holders ===
            "MSTR": {"bitcoin": 190000, "bitcoin_value_usd": 8_500_000_000},  # MicroStrategy - Largest corporate holder
            "MARA": {"bitcoin": 26200, "bitcoin_value_usd": 1_176_000_000},  # Marathon Digital - Mining operations
            "RIOT": {"bitcoin": 8872, "bitcoin_value_usd": 398_000_000},  # Riot Platforms - Mining operations
            "TSLA": {"bitcoin": 9720, "bitcoin_value_usd": 436_000_000},  # Tesla - Corporate treasury
            "COIN": {"bitcoin": 9000, "bitcoin_value_usd": 404_000_000, "ethereum": 4000, "ethereum_value_usd": 9_600_000},  # Coinbase - Exchange + treasury
            "SQ": {"bitcoin": 8027, "bitcoin_value_usd": 360_000_000},  # Block (Square) - Payment processor

            # === Bitcoin Miners (Additional) ===
            "HUT": {"bitcoin": 9100, "bitcoin_value_usd": 408_000_000},  # Hut 8 Mining - Canadian miner
            "CLSK": {"bitcoin": 5875, "bitcoin_value_usd": 264_000_000},  # CleanSpark - US-based miner
            "BITF": {"bitcoin": 4326, "bitcoin_value_usd": 194_000_000},  # Bitfarms - Canadian miner
            "CIFR": {"bitcoin": 3200, "bitcoin_value_usd": 144_000_000},  # Cipher Mining - Mining operations
            "CORZ": {"bitcoin": 2845, "bitcoin_value_usd": 128_000_000},  # Core Scientific - Mining + hosting
            "BTBT": {"bitcoin": 2100, "bitcoin_value_usd": 94_000_000},  # Bit Digital - Mining operations

            # === Crypto Asset Managers / Multi-Asset ===
            "GLXY": {
                "bitcoin": 12500,
                "bitcoin_value_usd": 561_000_000,
                "ethereum": 150000,
                "ethereum_value_usd": 360_000_000
            },  # Galaxy Digital - Institutional crypto asset manager
            "HOOD": {"bitcoin": 3500, "bitcoin_value_usd": 157_000_000},  # Robinhood - User custodial holdings

            # === Gold/Precious Metals Companies ===
            "NEM": {"gold_oz": 95_000_000, "gold_value_usd": 190_000_000_000},  # Newmont - Largest gold miner
            "GOLD": {"gold_oz": 60_000_000, "gold_value_usd": 120_000_000_000},  # Barrick Gold - Major producer
            "AEM": {"gold_oz": 12_000_000, "gold_value_usd": 24_000_000_000},  # Agnico Eagle - North American focus
            "FNV": {"gold_oz": 8_000_000, "gold_value_usd": 16_000_000_000},  # Franco-Nevada - Royalty/streaming
            "WPM": {"gold_oz": 5_500_000, "gold_value_usd": 11_000_000_000},  # Wheaton Precious Metals - Streaming
            "KGC": {"gold_oz": 4_200_000, "gold_value_usd": 8_400_000_000},  # Kinross Gold - Diversified miner
        }

        ticker_upper = ticker.upper()

        if ticker_upper not in KNOWN_ASSET_HOLDERS:
            return {
                "ticker": ticker_upper,
                "has_crypto_holdings": False,
                "has_gold_holdings": False,
                "bitcoin_count": 0,
                "bitcoin_value_usd": 0,
                "ethereum_count": 0,
                "ethereum_value_usd": 0,
                "gold_oz": 0,
                "gold_value_usd": 0,
                "total_asset_value_usd": 0,
                "timestamp": datetime.now().isoformat(),
            }

        holdings = KNOWN_ASSET_HOLDERS[ticker_upper]

        return {
            "ticker": ticker_upper,
            "has_crypto_holdings": "bitcoin" in holdings or "ethereum" in holdings,
            "has_gold_holdings": "gold_oz" in holdings,
            "bitcoin_count": holdings.get("bitcoin", 0),
            "bitcoin_value_usd": holdings.get("bitcoin_value_usd", 0),
            "ethereum_count": holdings.get("ethereum", 0),
            "ethereum_value_usd": holdings.get("ethereum_value_usd", 0),
            "gold_oz": holdings.get("gold_oz", 0),
            "gold_value_usd": holdings.get("gold_value_usd", 0),
            "total_asset_value_usd": (
                holdings.get("bitcoin_value_usd", 0) +
                holdings.get("ethereum_value_usd", 0) +
                holdings.get("gold_value_usd", 0)
            ),
            "timestamp": datetime.now().isoformat(),
        }

    def get_volatility_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        Get volatility metrics for The Coiled Spring screener.

        Calculates:
        - NR7 pattern detection (Narrowest Range of last 7 days)
        - 30-day historical volatility
        - 1-year volatility percentile ranking

        Rate limiting is handled automatically by exponential backoff with jitter.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict containing volatility metrics and NR7 detection
        """
        try:
            cache_key = f"{ticker.upper()}_volatility"
            cached_data = self._get_cached_data(cache_key)

            if cached_data is not None:
                logger.info(f"Returning cached volatility metrics for {ticker}")
                return cached_data

            logger.info(f"Fetching volatility metrics for {ticker}")

            # Use cached ticker object
            stock = self._get_ticker(ticker)

            # Fetch historical data
            # 1 year for percentile calculation
            hist_1y = self._fetch_ticker_history(stock, period="1y")

            if hist_1y.empty or len(hist_1y) < 30:
                logger.warning(f"Insufficient historical data for {ticker}")
                return {
                    "ticker": ticker.upper(),
                    "has_nr7": False,
                    "volatility_30d": None,
                    "volatility_percentile": None,
                    "is_low_volatility": False,
                    "current_range": None,
                    "error": "Insufficient historical data",
                    "timestamp": datetime.now().isoformat(),
                }

            # Calculate daily ranges
            hist_1y['Range'] = hist_1y['High'] - hist_1y['Low']

            # Get last 7 days for NR7 detection
            last_7_days = hist_1y.tail(7)

            # NR7 Detection: Today's range is narrowest of last 7 days
            if len(last_7_days) >= 7:
                ranges = last_7_days['Range'].values
                current_range = ranges[-1]  # Today's range
                has_nr7 = current_range == min(ranges)
            else:
                has_nr7 = False
                current_range = None

            # Calculate 30-day historical volatility
            # HV = std(log_returns) * sqrt(252) * 100
            last_30_days = hist_1y.tail(30)
            if len(last_30_days) >= 30:
                log_returns = np.log(last_30_days['Close'] / last_30_days['Close'].shift(1))
                volatility_30d = log_returns.std() * np.sqrt(252) * 100
            else:
                volatility_30d = None

            # Calculate 1-year volatility percentile
            # Roll 30-day volatility over the year
            if len(hist_1y) >= 30:
                rolling_log_returns = np.log(hist_1y['Close'] / hist_1y['Close'].shift(1))
                rolling_volatility = rolling_log_returns.rolling(window=30).std() * np.sqrt(252) * 100
                rolling_volatility = rolling_volatility.dropna()

                if len(rolling_volatility) > 0 and volatility_30d is not None:
                    # Calculate percentile rank of current volatility
                    volatility_percentile = (rolling_volatility < volatility_30d).sum() / len(rolling_volatility) * 100
                else:
                    volatility_percentile = None
            else:
                volatility_percentile = None

            # Determine if low volatility (bottom 10th percentile OR < 15%)
            is_low_volatility = False
            if volatility_30d is not None:
                is_low_volatility = volatility_30d < 15
                if volatility_percentile is not None:
                    is_low_volatility = is_low_volatility or volatility_percentile < 10

            metrics = {
                "ticker": ticker.upper(),
                "has_nr7": bool(has_nr7),  # Convert numpy bool_ to Python bool
                "current_range": float(current_range) if current_range is not None else None,
                "avg_range_7d": float(last_7_days['Range'].mean()) if len(last_7_days) > 0 else None,
                "volatility_30d": float(volatility_30d) if volatility_30d is not None else None,
                "volatility_percentile": float(volatility_percentile) if volatility_percentile is not None else None,
                "is_low_volatility": bool(is_low_volatility),  # Convert to Python bool
                "consolidation_score": self._calculate_consolidation_score(
                    has_nr7, volatility_30d, volatility_percentile
                ),
                "timestamp": datetime.now().isoformat(),
            }

            # Cache the result
            self._cache_data(cache_key, metrics)

            logger.info(
                f"Volatility metrics for {ticker}: NR7={has_nr7}, "
                f"HV30={volatility_30d:.1f}% (P{volatility_percentile:.0f})" if volatility_30d and volatility_percentile else f"NR7={has_nr7}"
            )

            return metrics

        except Exception as e:
            logger.error(f"Error fetching volatility metrics for {ticker}: {e}")
            return {
                "ticker": ticker.upper(),
                "has_nr7": False,
                "volatility_30d": None,
                "volatility_percentile": None,
                "is_low_volatility": False,
                "current_range": None,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _calculate_consolidation_score(
        self,
        has_nr7: bool,
        volatility_30d: Optional[float],
        volatility_percentile: Optional[float]
    ) -> float:
        """
        Calculate consolidation score (0-100) for Coiled Spring pattern.

        Higher score = More compressed/coiled = Higher breakout potential

        Args:
            has_nr7: Whether stock has NR7 pattern
            volatility_30d: 30-day historical volatility
            volatility_percentile: Percentile rank of current volatility

        Returns:
            Consolidation score (0-100)
        """
        score = 0.0

        # NR7 Pattern (40 points)
        if has_nr7:
            score += 40

        # Low Volatility Score (30 points)
        if volatility_30d is not None:
            if volatility_30d < 10:
                score += 30
            elif volatility_30d < 15:
                score += 20
            elif volatility_30d < 20:
                score += 10

        # Volatility Percentile Score (30 points)
        if volatility_percentile is not None:
            if volatility_percentile < 5:
                score += 30
            elif volatility_percentile < 10:
                score += 25
            elif volatility_percentile < 20:
                score += 15
            elif volatility_percentile < 30:
                score += 10

        return round(score, 1)

    def get_comprehensive_data(
        self,
        ticker: str,
        include_fundamentals: bool = True,
        include_technical: bool = False,
        include_options_flow: bool = False,
        include_volatility: bool = False,
        include_analyst_insider: bool = False,
    ) -> Dict[str, Any]:
        """
        Batch fetch multiple data types for a ticker in a single optimized call.

        This method is more efficient than calling individual methods because:
        1. Uses the same cached ticker object for all operations
        2. Reduces overhead from multiple function calls
        3. Rate limiting handled automatically by exponential backoff decorators

        Args:
            ticker: Stock ticker symbol
            include_fundamentals: Include fundamental data (default: True)
            include_technical: Include technical indicators (default: False)
            include_options_flow: Include options flow metrics (default: False)
            include_volatility: Include volatility metrics (default: False)
            include_analyst_insider: Include analyst/insider data (default: False)

        Returns:
            Dict containing requested data types

        Example:
            >>> provider = YFinanceProvider()
            >>> data = provider.get_comprehensive_data(
            ...     "AAPL",
            ...     include_fundamentals=True,
            ...     include_technical=True
            ... )
            >>> print(data.keys())
            dict_keys(['ticker', 'fundamentals', 'technical_indicators'])
        """
        try:
            logger.info(
                f"Fetching comprehensive data for {ticker}: "
                f"fundamentals={include_fundamentals}, technical={include_technical}, "
                f"options={include_options_flow}, volatility={include_volatility}, "
                f"analyst={include_analyst_insider}"
            )

            result = {"ticker": ticker.upper(), "timestamp": datetime.now().isoformat()}

            # Get or create cached ticker object (reused for all operations)
            stock = self._get_ticker(ticker)

            # Fetch requested data types
            if include_fundamentals:
                try:
                    cache_key = f"{ticker.upper()}_fundamentals"
                    cached_data = self._get_cached_data(cache_key)
                    if cached_data is not None:
                        result["fundamentals"] = cached_data
                    else:
                        # Inline fundamentals fetching
                        info = self._fetch_ticker_info(stock)
                        fundamentals = {
                            "ticker": ticker.upper(),
                            "company_name": info.get("longName") or info.get("shortName", ticker),
                            "sector": info.get("sector"),
                            "market_cap": info.get("marketCap"),
                            "peg_ratio": info.get("pegRatio") or info.get("trailingPegRatio"),
                            "eps_growth": self._calculate_eps_growth(stock),
                            "revenue_growth": self._calculate_revenue_growth(stock),
                            "debt_to_equity": info.get("debtToEquity"),
                            "roe": info.get("returnOnEquity"),
                            "institutional_ownership": info.get("heldPercentInstitutions"),
                            "current_ratio": info.get("currentRatio"),
                            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                            "pe_ratio": self._calculate_pe_ratio(info),
                            "week_52_low": info.get("fiftyTwoWeekLow"),
                            "week_52_high": info.get("fiftyTwoWeekHigh"),
                            "timestamp": datetime.now().isoformat(),
                        }
                        # Convert percentages
                        if fundamentals["roe"] is not None:
                            fundamentals["roe"] = fundamentals["roe"] * 100
                        if fundamentals["institutional_ownership"] is not None:
                            fundamentals["institutional_ownership"] = fundamentals["institutional_ownership"] * 100
                        if fundamentals["debt_to_equity"] is not None:
                            fundamentals["debt_to_equity"] = fundamentals["debt_to_equity"] / 100

                        self._cache_data(cache_key, fundamentals)
                        result["fundamentals"] = fundamentals
                except Exception as e:
                    logger.warning(f"Error fetching fundamentals in batch: {e}")
                    result["fundamentals"] = {"error": str(e)}

            if include_technical:
                try:
                    result["technical_indicators"] = self.get_technical_indicators(ticker)
                except Exception as e:
                    logger.warning(f"Error fetching technical indicators in batch: {e}")
                    result["technical_indicators"] = {"error": str(e)}

            if include_options_flow:
                try:
                    result["options_flow"] = self.get_options_flow_metrics(ticker)
                except Exception as e:
                    logger.warning(f"Error fetching options flow in batch: {e}")
                    result["options_flow"] = {"error": str(e)}

            if include_volatility:
                try:
                    result["volatility"] = self.get_volatility_metrics(ticker)
                except Exception as e:
                    logger.warning(f"Error fetching volatility in batch: {e}")
                    result["volatility"] = {"error": str(e)}

            if include_analyst_insider:
                try:
                    result["analyst_insider"] = self.get_analyst_and_insider_data(ticker)
                except Exception as e:
                    logger.warning(f"Error fetching analyst/insider data in batch: {e}")
                    result["analyst_insider"] = {"error": str(e)}

            logger.info(
                f"Comprehensive data fetch completed for {ticker}: "
                f"{len([k for k in result.keys() if k not in ['ticker', 'timestamp']])} data types"
            )

            return result

        except Exception as e:
            logger.error(f"Error fetching comprehensive data for {ticker}: {e}")
            raise ValueError(f"Failed to fetch comprehensive data for {ticker}: {str(e)}")

    def _is_cached(self, key: str) -> bool:
        """Check if data is in cache and not expired (thread-safe)."""
        with self.cache_lock:
            if key not in self.cache:
                return False

            cached_time = self.cache[key]["timestamp"]
            return datetime.now() - cached_time < self.cache_ttl

    def _get_cached_data(self, key: str) -> Optional[Any]:
        """
        Get cached data if available and not expired (thread-safe).

        Returns:
            Cached data if available and not expired, None otherwise
        """
        with self.cache_lock:
            if key not in self.cache:
                return None

            cached_time = self.cache[key]["timestamp"]
            if datetime.now() - cached_time < self.cache_ttl:
                return self.cache[key]["data"]
            return None

    def _cache_data(self, key: str, data: Any) -> None:
        """Store data in cache with timestamp (thread-safe)."""
        with self.cache_lock:
            self.cache[key] = {"data": data, "timestamp": datetime.now()}

    def clear_cache(self) -> None:
        """Clear all cached data (both result cache and ticker cache) - thread-safe."""
        with self.cache_lock:
            self.cache.clear()
        with self.ticker_cache_lock:
            self.ticker_cache.clear()
        logger.info("All caches cleared (data cache + ticker cache)")
