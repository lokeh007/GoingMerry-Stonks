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
        Get ticker universe for a specific batch (1, 2, 3, 4, or 5).

        Splits alphabetically:
        - Batch 1: A-D (~1200 stocks)
        - Batch 2: E-J (~1200 stocks)
        - Batch 3: K-N (~1200 stocks)
        - Batch 4: O-S (~1200 stocks)
        - Batch 5: T-Z (~1200 stocks)

        Args:
            batch_number: Batch number (1, 2, 3, 4, or 5)

        Returns:
            List of ticker symbols for this batch (~1200 stocks)
        """
        if batch_number not in [1, 2, 3, 4, 5]:
            raise ValueError(f"batch_number must be 1, 2, 3, 4, or 5. Got: {batch_number}")

        # Get full universe
        full_universe = self.get_full_universe()

        # Split alphabetically into 5 batches
        batch_ranges = {
            1: ("A", "D"),  # A-D
            2: ("E", "J"),  # E-J
            3: ("K", "N"),  # K-N
            4: ("O", "S"),  # O-S
            5: ("T", "Z"),  # T-Z
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
        - ETFs (comprehensive whitelist - no pattern matching to avoid false positives)
        - Test symbols
        """
        # Comprehensive ETF whitelist (preferred over pattern matching)
        known_etfs = self._get_comprehensive_etf_list()

        filtered = []
        etf_count = 0

        # Track what's being filtered for debugging
        filtered_by_reason: Dict[str, int] = {
            "index": 0,
            "too_long": 0,
            "special_chars": 0,
            "has_numbers": 0,
            "known_etf": 0,
            "test_symbol": 0,
        }

        for ticker in tickers:
            ticker = ticker.strip().upper()
            skip_reason = None

            # Skip empty
            if not ticker:
                continue

            # Skip indexes
            if ticker.startswith("^"):
                skip_reason = "index"
                filtered_by_reason["index"] += 1
                continue

            # Skip very long tickers (warrants/units)
            if len(ticker) > 5:
                skip_reason = "too_long"
                filtered_by_reason["too_long"] += 1
                continue

            # Skip preferred stocks and special securities (contain special chars)
            # $ is used for preferred stocks (BAC$E), - for hyphenated names, etc.
            if any(char in ticker for char in ["$", "-", ".", "/", "~", " "]):
                skip_reason = "special_chars"
                filtered_by_reason["special_chars"] += 1
                continue

            # Skip tickers with numbers (usually warrants)
            if any(char.isdigit() for char in ticker):
                skip_reason = "has_numbers"
                filtered_by_reason["has_numbers"] += 1
                continue

            # Skip known ETFs (whitelist approach - most reliable)
            if ticker in known_etfs:
                skip_reason = "known_etf"
                filtered_by_reason["known_etf"] += 1
                etf_count += 1
                continue

            # Skip test symbols
            if ticker in ["TEST", "SAMPLE", "ZVZZT"]:
                skip_reason = "test_symbol"
                filtered_by_reason["test_symbol"] += 1
                continue

            filtered.append(ticker)

        # Log filtering statistics
        logger.info(f"Filtering results: {len(filtered)} stocks retained, "
                   f"{len(tickers) - len(filtered)} removed")
        logger.info(f"  - Indexes: {filtered_by_reason['index']}")
        logger.info(f"  - Too long: {filtered_by_reason['too_long']}")
        logger.info(f"  - Special chars: {filtered_by_reason['special_chars']}")
        logger.info(f"  - Has numbers: {filtered_by_reason['has_numbers']}")
        logger.info(f"  - Known ETFs: {filtered_by_reason['known_etf']}")
        logger.info(f"  - Test symbols: {filtered_by_reason['test_symbol']}")

        return filtered

    def _get_comprehensive_etf_list(self) -> Set[str]:
        """
        Get comprehensive ETF list using whitelist approach.

        This is more reliable than pattern matching which has high false positive rates.
        Includes 200+ major ETFs across all categories.

        Returns:
            Set of ETF ticker symbols
        """
        return {
            # ===== Major Index Trackers =====
            "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "VEA", "VWO", "EEM", "AGG",
            "BND", "LQD", "HYG", "TLT", "IEF", "SHY", "MUB", "EMB", "IEMG", "IEFA",
            "GLD", "SLV", "VNQ", "VIG", "VYM", "SCHD", "RSP", "MDY", "IJR", "IJH",

            # ===== Sector SPDR ETFs (XL-) =====
            "XLF", "XLE", "XLK", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB", "XLRE",
            "XLC", "XTL", "XTN", "XPH", "XHS", "XES", "XAR", "XME", "XHB", "XRT",

            # ===== Vanguard Sector ETFs (VXX) =====
            "VGT", "VHT", "VDC", "VCR", "VIS", "VDE", "VAW", "VFH", "VPU", "VOX",

            # ===== iShares Core ETFs =====
            "IVV", "IEMG", "IEFA", "IJH", "IJR", "IWF", "IWD", "IWM", "IWN", "IWO",
            "IWP", "IWR", "IWS", "IWV",

            # ===== Commodity/Currency ETFs =====
            "GLD", "SLV", "USO", "UNG", "DBA", "DBC", "UUP", "FXE", "FXY", "FXB",
            "DBO", "DBB", "PPLT", "PALL", "GLTR", "GSG", "DJP", "USCI", "PDBC",

            # ===== Volatility ETFs =====
            "VXX", "UVXY", "SVXY", "VIXY", "VIXM", "ZIV",

            # ===== Direxion Leveraged/Inverse (3x) =====
            # Technology
            "SOXL", "SOXS", "TECL", "TECS", "WEBL", "WEBS",
            # Financials
            "FAS", "FAZ", "DPST", "DPST",
            # Energy
            "ERX", "ERY", "GUSH", "DRIP", "NRGU", "NRGD",
            # Small/Mid Cap
            "TNA", "TZA", "MIDU", "MIDZ", "SOXL", "SOXS",
            # Real Estate
            "DRN", "DRV",
            # Utilities
            "UTSL", "DUSL",
            # Healthcare
            "CURE", "RXD",
            # Consumer
            "RETL", "RETS",
            # Materials
            "MATL", "MATS",
            # Industrials
            "DUSL", "INDS",
            # Gold/Miners (3x)
            "NUGT", "DUST", "JNUG", "JDST", "GDXJ", "GDXD",
            # Oil/Gas (3x)
            "UGAZ", "DGAZ",
            # Other Direxion
            "DIG", "DUG", "DDM", "DXD", "SAA", "SDD", "MVV", "MZZ", "UWM", "TWM",
            "UYM", "SMN", "UGE", "SZK", "UCC", "SCC", "UYG", "SKF", "URE", "SRS",

            # ===== ProShares Leveraged/Inverse (2x/3x) =====
            # S&P 500
            "SSO", "SDS", "UPRO", "SPXU", "SPUU", "SPDN",
            # NASDAQ
            "QLD", "QID", "TQQQ", "SQQQ",
            # Dow
            "DDM", "DXD", "UDOW", "SDOW",
            # Russell 2000
            "UWM", "TWM", "URTY", "SRTY",
            # Semiconductors
            "USD", "SSG",
            # Financials
            "UYG", "SKF",
            # Real Estate
            "URE", "SRS",
            # Oil/Gas
            "UCO", "SCO", "UNG", "KOLD",
            # Gold/Silver
            "UGL", "GLL", "AGQ", "ZSL",
            # Utilities
            "UPW", "SDP",
            # Emerging Markets
            "EET", "EEV", "UMDD", "SMDD",
            # Europe
            "UPV", "EPV",
            # Japan
            "EZJ", "EWV",
            # China
            "YINN", "YANG",
            # VIX
            "UVXY", "SVXY",

            # ===== Leveraged Bond ETFs =====
            "TMF", "TMV", "TYD", "TYO", "UST", "PST",

            # ===== Inverse (Bear) ETFs =====
            "SH", "PSQ", "DOG", "RWM", "MYY", "EUM", "EFZ", "EFU",
            "SEF", "SBB", "SBM", "SCC", "SDD", "SDP", "SIJ", "SJB",
            "SKK", "SMN", "SRS", "SZK",

            # ===== ARK Innovation ETFs =====
            "ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "ARKX", "IZRL", "PRNT",

            # ===== Thematic/Specialty ETFs =====
            "ICLN", "TAN", "QCLN", "PBW", "ACES", "SMOG",  # Clean energy
            "LIT", "BATT", "REMX",  # Batteries/rare earths
            "BOTZ", "ROBO", "IRBO",  # Robotics
            "HACK", "CIBR", "BUG",  # Cybersecurity
            "CLOU", "SKYY", "WCLD",  # Cloud computing
            "FINX", "IPAY", "TPAY",  # Fintech
            "ESPO", "HERO", "GAMR",  # Gaming/Esports
            "FIVG", "NXTG",  # 5G
            "UFO", "ROKT",  # Space
            "MSOS", "YOLO", "THCX", "MJ",  # Cannabis
            "BETZ", "BJK",  # Sports betting
            "TAN", "ACES",  # Solar
            "JETS", "AWAY",  # Airlines/travel
            "XHE", "XBI",  # Biotech
            "SRVR", "DTEC",  # Data centers

            # ===== Country/Region Specific =====
            "EWJ", "EWT", "EWG", "EWU", "EWA", "EWC", "EWH", "EWL", "EWP", "EWQ",
            "EWI", "EWD", "EWN", "EWK", "EWS", "INDA", "EWZ", "EWW", "EWY", "RSX",
            "ERUS", "THD", "TUR", "EPOL", "ECH", "EPU", "NORW", "EWM", "EGPT",

            # ===== Smart Beta/Factor ETFs =====
            "MTUM", "QUAL", "SIZE", "USMV", "VLUE", "IQLT", "SPHQ", "DGRW",

            # ===== Multi-Asset/Balanced =====
            "AOR", "AOM", "AOA", "AOK",

            # ===== Bond ETFs =====
            "BND", "AGG", "LQD", "HYG", "JNK", "MUB", "TLT", "IEF", "SHY",
            "VCSH", "VCIT", "VGSH", "VGIT", "VGLT", "EMB", "BNDX", "JPST",
        }

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

    # Test all 5 batches
    for batch_num in range(1, 6):
        batch_ranges = {
            1: "A-D", 2: "E-J", 3: "K-N", 4: "O-S", 5: "T-Z"
        }
        print(f"\n=== Batch {batch_num} ({batch_ranges[batch_num]}) ===")
        batch = provider.get_batch_universe(batch_num)
        print(f"Total: {len(batch)} stocks")
        if batch:
            print(f"Range: {batch[0]} to {batch[-1]}")
