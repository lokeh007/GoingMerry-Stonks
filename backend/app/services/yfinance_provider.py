"""
YFinance Data Provider Module.

This module provides market data and technical indicators using the yfinance library.
Used for 15-minute delayed data that complements the Polygon.io real-time feed.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from functools import wraps
import yfinance as yf
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def rate_limit(min_interval: float = 0.1):
    """
    Decorator to rate limit API calls.

    Ensures minimum time interval between calls to prevent API throttling.

    Args:
        min_interval: Minimum seconds between calls (default: 0.1 = 100ms)
    """
    last_called = {}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            now = time.time()

            if func_name in last_called:
                elapsed = now - last_called[func_name]
                if elapsed < min_interval:
                    sleep_time = min_interval - elapsed
                    logger.debug(f"Rate limiting: sleeping {sleep_time:.3f}s before {func_name}")
                    time.sleep(sleep_time)

            result = func(*args, **kwargs)
            last_called[func_name] = time.time()
            return result

        return wrapper

    return decorator


class YFinanceProvider:
    """
    Provider for market data and technical indicators using yfinance.

    This class handles:
    - Technical indicator calculation (RSI, MACD)
    - Historical OHLCV data for pattern detection
    - VIX (Volatility Index) data
    - Stock universe fetching (NYSE + NASDAQ)

    Note: Data is 15-minute delayed (free tier)
    """

    def __init__(self):
        """Initialize the YFinance provider."""
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(minutes=15)  # Match data delay
        logger.info("YFinanceProvider initialized")

    @rate_limit(min_interval=0.1)
    def get_technical_indicators(
        self, ticker: str, period: str = "6mo"
    ) -> Dict[str, Any]:
        """
        Fetch technical indicators for a stock.

        Args:
            ticker: Stock ticker symbol
            period: Time period (1mo, 3mo, 6mo, 1y, 2y, 5y)

        Returns:
            Dict containing RSI, MACD, and other indicators

        Raises:
            ValueError: If ticker is invalid or data unavailable
        """
        try:
            cache_key = f"{ticker}_{period}_indicators"
            if self._is_cached(cache_key):
                logger.info(f"Returning cached indicators for {ticker}")
                return self.cache[cache_key]["data"]

            logger.info(f"Fetching technical indicators for {ticker} ({period})")

            # Fetch historical data
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)

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

    @rate_limit(min_interval=0.1)
    def get_historical_data(
        self, ticker: str, period: str = "6mo", interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for pattern detection.

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
            cache_key = f"{ticker}_{period}_{interval}_hist"
            if self._is_cached(cache_key):
                logger.info(f"Returning cached historical data for {ticker}")
                return self.cache[cache_key]["data"]

            logger.info(f"Fetching historical data for {ticker} ({period}, {interval})")

            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)

            if df.empty:
                raise ValueError(f"No historical data available for {ticker}")

            # Cache the results
            self._cache_data(cache_key, df)

            logger.info(f"Fetched {len(df)} data points for {ticker}")

            return df

        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {e}")
            raise ValueError(f"Failed to fetch historical data for {ticker}: {str(e)}")

    @rate_limit(min_interval=0.1)
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
            cache_key = f"{ticker}_fundamentals"
            if self._is_cached(cache_key):
                logger.info(f"Returning cached fundamentals for {ticker}")
                return self.cache[cache_key]["data"]

            logger.info(f"Fetching fundamentals for {ticker}")

            stock = yf.Ticker(ticker)
            info = stock.info

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
            quarterly_financials = stock.quarterly_financials
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
            annual_financials = stock.financials
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
            quarterly_financials = stock.quarterly_financials
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
            annual_financials = stock.financials
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

    @rate_limit(min_interval=0.2)
    def get_vix_data(self) -> Dict[str, Any]:
        """
        Fetch VIX (Volatility Index) data.

        Returns:
            Dict containing VIX value and market regime

        Raises:
            ValueError: If VIX data unavailable
        """
        try:
            cache_key = "vix_data"
            if self._is_cached(cache_key):
                logger.info("Returning cached VIX data")
                return self.cache[cache_key]["data"]

            logger.info("Fetching VIX data")

            vix = yf.Ticker("^VIX")
            vix_data = vix.history(period="1d")

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

    def _is_cached(self, key: str) -> bool:
        """Check if data is in cache and not expired."""
        if key not in self.cache:
            return False

        cached_time = self.cache[key]["timestamp"]
        return datetime.now() - cached_time < self.cache_ttl

    def _cache_data(self, key: str, data: Any) -> None:
        """Store data in cache with timestamp."""
        self.cache[key] = {"data": data, "timestamp": datetime.now()}

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Cache cleared")
