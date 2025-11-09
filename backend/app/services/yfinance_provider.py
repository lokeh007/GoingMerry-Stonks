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

    def get_stock_universe(
        self, exchange: str = "NASDAQ", limit: Optional[int] = None
    ) -> List[str]:
        """
        Get list of available tickers from specified exchange.

        Args:
            exchange: Exchange name (NASDAQ, NYSE, ALL)
            limit: Maximum number of tickers to return (None = all)

        Returns:
            List of ticker symbols

        Note:
            This is a simplified implementation. For production, consider using
            a dedicated ticker database or API.
        """
        try:
            logger.info(f"Fetching stock universe for {exchange}")

            # Common popular stocks across exchanges (starter set)
            # In production, this would query a ticker database
            nasdaq_stocks = [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "META",
                "NVDA",
                "TSLA",
                "NFLX",
                "ADBE",
                "AVGO",
                "CSCO",
                "INTC",
                "AMD",
                "QCOM",
                "TXN",
                "INTU",
                "AMAT",
                "MU",
                "ADI",
                "LRCX",
                "KLAC",
                "MRVL",
                "SNPS",
                "CDNS",
                "FTNT",
                "WDAY",
                "TEAM",
                "PANW",
                "CRWD",
                "ZS",
                "DDOG",
                "NET",
                "SNOW",
                "PLTR",
                "SOFI",
            ]

            nyse_stocks = [
                "JPM",
                "BAC",
                "WFC",
                "C",
                "GS",
                "MS",
                "AXP",
                "V",
                "MA",
                "PYPL",
                "BLK",
                "SCHW",
                "USB",
                "PNC",
                "TFC",
                "BK",
                "STT",
                "WMT",
                "HD",
                "CVS",
                "UNH",
                "JNJ",
                "PFE",
                "ABBV",
                "LLY",
                "MRK",
                "TMO",
                "ABT",
                "DHR",
                "BMY",
                "AMGN",
                "GILD",
                "VRTX",
                "REGN",
            ]

            if exchange.upper() == "NASDAQ":
                tickers = nasdaq_stocks
            elif exchange.upper() == "NYSE":
                tickers = nyse_stocks
            elif exchange.upper() == "ALL":
                tickers = list(set(nasdaq_stocks + nyse_stocks))
            else:
                raise ValueError(f"Unknown exchange: {exchange}")

            if limit:
                tickers = tickers[:limit]

            logger.info(f"Returning {len(tickers)} tickers from {exchange}")

            return sorted(tickers)

        except Exception as e:
            logger.error(f"Error fetching stock universe: {e}")
            raise ValueError(f"Failed to fetch stock universe: {str(e)}")

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
