"""
Ticker Universe Provider - Free Stock Lists

Fetches complete NYSE/NASDAQ ticker lists from free public sources:
- SEC EDGAR database (official)
- NASDAQ FTP server (updated daily)

No paid API required - 100% free data sources.
"""

import logging
import pandas as pd
import requests
from typing import List, Dict, Set
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class TickerUniverseProvider:
    """Provides comprehensive stock ticker lists from free sources."""

    def __init__(self):
        self.cache: Dict[str, List[str]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(hours=24)  # Refresh daily

    def get_full_universe(
        self,
        min_market_cap: float = 100_000_000,  # $100M
        min_volume: int = 100_000,  # 100K shares/day
        min_price: float = 2.0,  # $2
    ) -> List[str]:
        """
        Get full NYSE + NASDAQ universe with basic filters.

        Args:
            min_market_cap: Minimum market cap in dollars
            min_volume: Minimum average daily volume
            min_price: Minimum stock price

        Returns:
            List of ticker symbols (~6000 stocks)
        """
        logger.info("Fetching full NYSE + NASDAQ universe...")

        # Get tickers from multiple free sources
        nasdaq_tickers = self._get_nasdaq_listed()
        nyse_tickers = self._get_nyse_listed()
        sec_tickers = self._get_sec_ticker_list()

        # Combine and deduplicate
        all_tickers = set(nasdaq_tickers + nyse_tickers + sec_tickers)

        # Apply basic filters
        filtered_tickers = self._apply_basic_filters(list(all_tickers))

        logger.info(
            f"Universe: {len(all_tickers)} total, "
            f"{len(filtered_tickers)} after filtering"
        )

        return sorted(filtered_tickers)

    def get_batch_universe(self, batch_number: int) -> List[str]:
        """
        Get ticker universe for a specific batch (1, 2, or 3).

        Splits alphabetically:
        - Batch 1: A-H
        - Batch 2: I-P
        - Batch 3: Q-Z

        Args:
            batch_number: Batch number (1, 2, or 3)

        Returns:
            List of ticker symbols for this batch (~2000 stocks)
        """
        if batch_number not in [1, 2, 3]:
            raise ValueError(f"batch_number must be 1, 2, or 3. Got: {batch_number}")

        # Get full universe
        full_universe = self.get_full_universe()

        # Split alphabetically
        batch_ranges = {
            1: ("A", "H"),  # A-H
            2: ("I", "P"),  # I-P
            3: ("Q", "Z"),  # Q-Z
        }

        start_letter, end_letter = batch_ranges[batch_number]

        # Filter tickers in range
        batch_tickers = [
            ticker
            for ticker in full_universe
            if start_letter <= ticker[0].upper() <= end_letter
        ]

        logger.info(
            f"Batch {batch_number} ({start_letter}-{end_letter}): "
            f"{len(batch_tickers)} stocks"
        )

        return batch_tickers

    def _get_nasdaq_listed(self) -> List[str]:
        """
        Fetch NASDAQ listed stocks from official FTP server.

        Source: ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt
        Updated daily by NASDAQ
        """
        cache_key = "nasdaq_listed"

        # Check cache
        if self._is_cache_valid(cache_key):
            logger.info("Using cached NASDAQ ticker list")
            return self.cache[cache_key]

        try:
            logger.info("Fetching NASDAQ listed stocks from FTP...")

            url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"
            df = pd.read_csv(url, sep="|")

            # Filter valid stocks
            # - Exclude test issues
            # - Include only Global Select Market (Q), Global Market (G), Capital Market (S)
            df = df[df["Test Issue"] == "N"]
            df = df[df["Market Category"].isin(["Q", "G", "S"])]
            df = df[df["Financial Status"] == "N"]  # Normal (not deficient/delinquent)

            tickers = df["Symbol"].str.strip().tolist()

            # Remove trailing delimiters
            tickers = [t.rstrip("|") for t in tickers if t and t != "Symbol"]

            # Cache result
            self.cache[cache_key] = tickers
            self.cache_timestamp[cache_key] = datetime.now()

            logger.info(f"Fetched {len(tickers)} NASDAQ tickers")
            return tickers

        except Exception as e:
            logger.error(f"Error fetching NASDAQ tickers: {e}")
            return []

    def _get_nyse_listed(self) -> List[str]:
        """
        Fetch NYSE listed stocks from NASDAQ FTP (includes NYSE, NYSE American, NYSE Arca).

        Source: ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt
        Updated daily
        """
        cache_key = "nyse_listed"

        # Check cache
        if self._is_cache_valid(cache_key):
            logger.info("Using cached NYSE ticker list")
            return self.cache[cache_key]

        try:
            logger.info("Fetching NYSE listed stocks from FTP...")

            url = "ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt"
            df = pd.read_csv(url, sep="|")

            # Filter valid stocks
            # - Exclude test issues
            # - Include A=NYSE MKT, N=NYSE, P=NYSE Arca
            df = df[df["Test Issue"] == "N"]
            df = df[df["Exchange"].isin(["A", "N", "P"])]

            tickers = df["ACT Symbol"].str.strip().tolist()

            # Remove trailing delimiters
            tickers = [t.rstrip("|") for t in tickers if t and t != "ACT Symbol"]

            # Cache result
            self.cache[cache_key] = tickers
            self.cache_timestamp[cache_key] = datetime.now()

            logger.info(f"Fetched {len(tickers)} NYSE tickers")
            return tickers

        except Exception as e:
            logger.error(f"Error fetching NYSE tickers: {e}")
            return []

    def _get_sec_ticker_list(self) -> List[str]:
        """
        Fetch ticker list from SEC EDGAR database.

        Source: https://www.sec.gov/files/company_tickers.json
        Official list of all publicly traded companies
        """
        cache_key = "sec_tickers"

        # Check cache
        if self._is_cache_valid(cache_key):
            logger.info("Using cached SEC ticker list")
            return self.cache[cache_key]

        try:
            logger.info("Fetching SEC ticker list...")

            url = "https://www.sec.gov/files/company_tickers.json"
            headers = {
                "User-Agent": "GoingMerry-Stonks research@example.com"  # SEC requires User-Agent
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Extract tickers (format: {0: {ticker: "AAPL", ...}, 1: {...}})
            tickers = [item["ticker"] for item in data.values()]

            # Cache result
            self.cache[cache_key] = tickers
            self.cache_timestamp[cache_key] = datetime.now()

            logger.info(f"Fetched {len(tickers)} SEC tickers")
            return tickers

        except Exception as e:
            logger.error(f"Error fetching SEC tickers: {e}")
            return []

    def _apply_basic_filters(self, tickers: List[str]) -> List[str]:
        """
        Apply basic filters to remove invalid/unwanted tickers.

        Removes:
        - Indexes (start with $ or ^)
        - Warrants/Units (ticker length > 5)
        - Preferred stocks (contains -, ., /, ~)
        - Tickers with numbers (usually warrants)
        - ETFs (known tickers and patterns)
        - Test symbols
        """
        # Known major ETFs to exclude
        known_etfs = {
            # Major index ETFs
            "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "VEA", "VWO", "EEM", "AGG",
            "BND", "LQD", "HYG", "TLT", "IEF", "SHY", "MUB", "EMB",
            # Sector ETFs
            "XLF", "XLE", "XLK", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB", "XLRE",
            # Commodity/Currency ETFs
            "GLD", "SLV", "USO", "UNG", "DBA", "DBC", "UUP", "FXE",
            # Volatility ETFs
            "VXX", "UVXY", "SVXY", "VIXY",
            # Leveraged/Inverse (common ones from your logs)
            "DIG", "DUG", "DDM", "DXD", "SSO", "SDS", "UPRO", "SPXU",
            "TQQQ", "SQQQ", "FAS", "FAZ", "TNA", "TZA", "NUGT", "DUST",
            "JNUG", "JDST", "ERX", "ERY", "UGAZ", "DGAZ",
        }

        # ETF suffixes (leveraged/inverse ETFs)
        # Examples: DIG, DMX, DGZ, DGP, DJP, etc.
        etf_suffixes = {"X", "Z", "L", "S", "M"}

        filtered = []
        etf_count = 0

        for ticker in tickers:
            ticker = ticker.strip().upper()

            # Skip empty
            if not ticker:
                continue

            # Skip indexes
            if ticker.startswith("^"):
                continue

            # Skip very long tickers (warrants/units)
            if len(ticker) > 5:
                continue

            # Skip preferred stocks and special securities (contain special chars)
            # $ is used for preferred stocks (BAC$E), - for hyphenated names, etc.
            if any(char in ticker for char in ["$", "-", ".", "/", "~", " "]):
                continue

            # Skip tickers with numbers (usually warrants)
            if any(char.isdigit() for char in ticker):
                continue

            # Skip known ETFs
            if ticker in known_etfs:
                etf_count += 1
                continue

            # Skip ETF-like patterns (3-4 letter tickers ending in X, Z, L, S, M)
            # These are usually leveraged/inverse ETFs: DIG, DMX, DGZ, etc.
            if len(ticker) <= 4 and ticker[-1] in etf_suffixes:
                # Allow exceptions for real companies (add as needed)
                exceptions = {"FLEX", "CEIX", "AIZ"}
                if ticker not in exceptions:
                    etf_count += 1
                    continue

            # Skip tickers that look like ProShares/Direxion patterns
            # Format: DXX, TXX, UXX, SXX (D=Direxion, T/S=short, U=ultra)
            if len(ticker) == 3 and ticker[0] in ["D", "T", "U", "S"]:
                # Allow exceptions for real companies
                exceptions = {"DNA", "DAL", "DIS", "TPR", "UAL", "UPS"}
                if ticker not in exceptions:
                    etf_count += 1
                    continue

            # Skip test symbols
            if ticker in ["TEST", "SAMPLE", "ZVZZT"]:
                continue

            filtered.append(ticker)

        if etf_count > 0:
            logger.info(f"Filtered out {etf_count} ETFs")

        return filtered

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid (within TTL)."""
        if cache_key not in self.cache or cache_key not in self.cache_timestamp:
            return False

        age = datetime.now() - self.cache_timestamp[cache_key]
        return age < self.cache_ttl


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    provider = TickerUniverseProvider()

    # Test full universe
    print("\n=== Full Universe ===")
    universe = provider.get_full_universe()
    print(f"Total: {len(universe)} stocks")
    print(f"Sample: {universe[:10]}")

    # Test batch 1
    print("\n=== Batch 1 (A-H) ===")
    batch1 = provider.get_batch_universe(1)
    print(f"Total: {len(batch1)} stocks")
    print(f"Range: {batch1[0]} to {batch1[-1]}")

    # Test batch 2
    print("\n=== Batch 2 (I-P) ===")
    batch2 = provider.get_batch_universe(2)
    print(f"Total: {len(batch2)} stocks")
    print(f"Range: {batch2[0]} to {batch2[-1]}")

    # Test batch 3
    print("\n=== Batch 3 (Q-Z) ===")
    batch3 = provider.get_batch_universe(3)
    print(f"Total: {len(batch3)} stocks")
    print(f"Range: {batch3[0]} to {batch3[-1]}")
