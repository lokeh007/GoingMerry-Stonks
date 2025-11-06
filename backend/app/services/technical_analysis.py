"""
Technical Analysis Service Module.

This module provides technical indicator calculations including RSI, MACD,
and various moving averages for stock price analysis.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

import numpy as np
import pandas as pd
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TechnicalAnalysisError(Exception):
    """Base exception for technical analysis operations."""
    pass


class TechnicalAnalysisProvider:
    """
    Service class for calculating technical indicators.

    This class provides methods for computing common technical indicators
    used in stock analysis including RSI, MACD, EMAs, and SMAs.
    """

    def __init__(self):
        """Initialize the Technical Analysis Provider."""
        logger.info("Initialized TechnicalAnalysisProvider")

    def get_price_history(
        self,
        ticker: str,
        period: str = "6mo",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical price data for a ticker.

        Args:
            ticker: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            DataFrame with OHLCV data

        Raises:
            TechnicalAnalysisError: If unable to fetch data
        """
        try:
            logger.info(f"Fetching price history for {ticker} (period={period}, interval={interval})")

            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)

            if hist.empty:
                raise TechnicalAnalysisError(f"No price data available for {ticker}")

            logger.info(f"Retrieved {len(hist)} data points for {ticker}")
            return hist

        except Exception as e:
            logger.error(f"Error fetching price history for {ticker}: {str(e)}")
            raise TechnicalAnalysisError(f"Failed to fetch price history: {str(e)}")

    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA).

        EMA gives more weight to recent prices, making it more responsive
        to new information compared to SMA.

        Args:
            data: Price data series
            period: Number of periods for EMA calculation

        Returns:
            Series containing EMA values
        """
        return data.ewm(span=period, adjust=False).mean()

    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA).

        Args:
            data: Price data series
            period: Number of periods for SMA calculation

        Returns:
            Series containing SMA values
        """
        return data.rolling(window=period).mean()

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        RSI measures the magnitude of recent price changes to evaluate
        overbought or oversold conditions. Values range from 0 to 100.

        Interpretation:
        - RSI > 70: Overbought (potential sell signal)
        - RSI < 30: Oversold (potential buy signal)
        - RSI = 50: Neutral

        Args:
            data: Price data series
            period: Lookback period (default: 14)

        Returns:
            Series containing RSI values
        """
        # Calculate price changes
        delta = data.diff()

        # Separate gains and losses
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)

        # Calculate average gain and loss
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

        # Calculate RS (Relative Strength)
        rs = avg_gain / avg_loss

        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_macd(
        self,
        data: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        MACD is a trend-following momentum indicator that shows the
        relationship between two moving averages.

        Components:
        - MACD Line: Fast EMA - Slow EMA
        - Signal Line: EMA of MACD Line
        - Histogram: MACD Line - Signal Line

        Signals:
        - MACD crosses above Signal: Bullish signal
        - MACD crosses below Signal: Bearish signal
        - Histogram > 0: Bullish momentum
        - Histogram < 0: Bearish momentum

        Args:
            data: Price data series
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line EMA period (default: 9)

        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' Series
        """
        # Calculate EMAs
        ema_fast = self.calculate_ema(data, fast_period)
        ema_slow = self.calculate_ema(data, slow_period)

        # Calculate MACD line
        macd_line = ema_fast - ema_slow

        # Calculate signal line
        signal_line = self.calculate_ema(macd_line, signal_period)

        # Calculate histogram
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def calculate_bollinger_bands(
        self,
        data: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.

        Bollinger Bands consist of a middle band (SMA) and two outer bands
        that are standard deviations away from the middle band.

        Args:
            data: Price data series
            period: Period for SMA calculation (default: 20)
            std_dev: Number of standard deviations (default: 2.0)

        Returns:
            Dictionary with 'upper', 'middle', and 'lower' band Series
        """
        middle_band = self.calculate_sma(data, period)
        rolling_std = data.rolling(window=period).std()

        upper_band = middle_band + (std_dev * rolling_std)
        lower_band = middle_band - (std_dev * rolling_std)

        return {
            'upper': upper_band,
            'middle': middle_band,
            'lower': lower_band
        }

    def get_technical_analysis(
        self,
        ticker: str,
        period: str = "6mo",
        interval: str = "1d",
        indicators: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive technical analysis data for a ticker.

        Args:
            ticker: Stock ticker symbol
            period: Time period for historical data
            interval: Data interval
            indicators: List of indicators to calculate (default: all)
                Available: 'rsi', 'macd', 'ema12', 'ema26', 'ema50', 'ema200',
                          'sma20', 'sma50', 'sma200', 'bollinger'

        Returns:
            Dictionary containing price history and calculated indicators

        Example:
            >>> provider = TechnicalAnalysisProvider()
            >>> analysis = provider.get_technical_analysis('AAPL', indicators=['rsi', 'macd'])
        """
        try:
            logger.info(f"Generating technical analysis for {ticker}")

            # Fetch price history
            hist = self.get_price_history(ticker, period, interval)

            # If no indicators specified, calculate all
            if indicators is None:
                indicators = ['rsi', 'macd', 'ema12', 'ema26', 'ema50', 'ema200',
                            'sma20', 'sma50', 'sma200', 'bollinger']

            # Extract close prices for calculations
            close_prices = hist['Close']

            # Calculate requested indicators
            result = {
                'ticker': ticker.upper(),
                'period': period,
                'interval': interval,
                'data_points': len(hist),
                'price_data': {
                    'dates': hist.index.strftime('%Y-%m-%d').tolist(),
                    'open': hist['Open'].tolist(),
                    'high': hist['High'].tolist(),
                    'low': hist['Low'].tolist(),
                    'close': hist['Close'].tolist(),
                    'volume': hist['Volume'].tolist(),
                },
                'indicators': {}
            }

            # RSI
            if 'rsi' in indicators:
                rsi = self.calculate_rsi(close_prices)
                result['indicators']['rsi'] = rsi.fillna(0).tolist()
                result['indicators']['rsi_current'] = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

            # MACD
            if 'macd' in indicators:
                macd_data = self.calculate_macd(close_prices)
                result['indicators']['macd'] = {
                    'macd_line': macd_data['macd'].fillna(0).tolist(),
                    'signal_line': macd_data['signal'].fillna(0).tolist(),
                    'histogram': macd_data['histogram'].fillna(0).tolist(),
                }

            # EMAs
            for period_num in [12, 26, 50, 200]:
                indicator_name = f'ema{period_num}'
                if indicator_name in indicators:
                    ema = self.calculate_ema(close_prices, period_num)
                    result['indicators'][indicator_name] = ema.fillna(0).tolist()

            # SMAs
            for period_num in [20, 50, 200]:
                indicator_name = f'sma{period_num}'
                if indicator_name in indicators:
                    sma = self.calculate_sma(close_prices, period_num)
                    result['indicators'][indicator_name] = sma.fillna(0).tolist()

            # Bollinger Bands
            if 'bollinger' in indicators:
                bb = self.calculate_bollinger_bands(close_prices)
                result['indicators']['bollinger'] = {
                    'upper': bb['upper'].fillna(0).tolist(),
                    'middle': bb['middle'].fillna(0).tolist(),
                    'lower': bb['lower'].fillna(0).tolist(),
                }

            result['timestamp'] = datetime.now().isoformat()

            logger.info(f"Successfully generated technical analysis for {ticker}")
            return result

        except Exception as e:
            logger.error(f"Error generating technical analysis for {ticker}: {str(e)}")
            raise TechnicalAnalysisError(f"Failed to generate technical analysis: {str(e)}")
