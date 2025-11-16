"""
Delisted Ticker Cache Service

Tracks tickers that have been delisted or have no data available to avoid
wasting API calls on invalid tickers in future screener runs.

Features:
- Auto-detection: Automatically adds tickers to blacklist when "no data" errors occur
- Firestore persistence: Blacklist survives across Cloud Run job executions
- TTL-based retry: Automatically retries blacklisted tickers after 30 days
- Metrics tracking: Logs statistics on blacklisted tickers

Firestore Structure:
  delisted_tickers/{ticker}
    - ticker: str (ticker symbol)
    - first_detected: timestamp (when first blacklisted)
    - last_checked: timestamp (last time we tried to fetch data)
    - error_type: str ("no_data", "404", "not_found")
    - retry_after: timestamp (when to retry this ticker)
    - failure_count: int (number of times this ticker failed)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Set, Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)


class DelistedTickerCache:
    """
    Manages a persistent cache of delisted/invalid tickers in Firestore.

    Usage:
        cache = DelistedTickerCache()

        # Check if ticker is blacklisted
        if cache.is_blacklisted("DMII"):
            print("Skipping delisted ticker")

        # Add ticker to blacklist
        cache.add_to_blacklist("DMII", error_type="no_data")

        # Get all blacklisted tickers
        blacklist = cache.get_blacklisted_tickers()
    """

    COLLECTION_NAME = "delisted_tickers"
    DEFAULT_TTL_DAYS = 30  # Retry after 30 days

    def __init__(self, ttl_days: int = DEFAULT_TTL_DAYS):
        """
        Initialize Firestore client and cache.

        Args:
            ttl_days: Number of days before retrying a blacklisted ticker
        """
        self.db = firestore.Client()
        self.ttl_days = ttl_days
        self._cache: Optional[Set[str]] = None  # In-memory cache for single run
        self._cache_loaded = False

        logger.info(f"DelistedTickerCache initialized (TTL: {ttl_days} days)")

    def is_blacklisted(self, ticker: str) -> bool:
        """
        Check if a ticker is currently blacklisted.

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if ticker should be skipped, False if we should try it
        """
        # Lazy load cache on first check
        if not self._cache_loaded:
            self._load_cache()

        return ticker.upper() in self._cache

    def add_to_blacklist(
        self,
        ticker: str,
        error_type: str = "no_data"
    ) -> None:
        """
        Add a ticker to the blacklist (or update if already exists).

        Args:
            ticker: Stock ticker symbol
            error_type: Type of error ("no_data", "404", "not_found")
        """
        ticker = ticker.upper()
        now = datetime.now(timezone.utc)
        retry_after = now + timedelta(days=self.ttl_days)

        try:
            doc_ref = self.db.collection(self.COLLECTION_NAME).document(ticker)
            doc = doc_ref.get()

            if doc.exists:
                # Update existing entry
                data = doc.to_dict()
                doc_ref.update({
                    "last_checked": now,
                    "retry_after": retry_after,
                    "failure_count": firestore.Increment(1),
                    "error_type": error_type,  # Update to latest error type
                })
                logger.debug(
                    f"Updated blacklist entry for {ticker} "
                    f"(failures: {data.get('failure_count', 0) + 1})"
                )
            else:
                # Create new entry
                doc_ref.set({
                    "ticker": ticker,
                    "first_detected": now,
                    "last_checked": now,
                    "error_type": error_type,
                    "retry_after": retry_after,
                    "failure_count": 1,
                })
                logger.info(f"Added {ticker} to blacklist (error: {error_type})")

            # Update in-memory cache
            if self._cache is not None:
                self._cache.add(ticker)

        except Exception as e:
            logger.error(f"Error adding {ticker} to blacklist: {e}")

    def add_batch_to_blacklist(
        self,
        tickers: List[str],
        error_type: str = "no_data"
    ) -> None:
        """
        Add multiple tickers to blacklist efficiently using batch writes.

        Args:
            tickers: List of ticker symbols to blacklist
            error_type: Type of error for all tickers
        """
        if not tickers:
            return

        now = datetime.now(timezone.utc)
        retry_after = now + timedelta(days=self.ttl_days)

        try:
            # Firestore batch writes (max 500 operations)
            batch = self.db.batch()
            operations = 0

            for ticker in tickers:
                ticker = ticker.upper()
                doc_ref = self.db.collection(self.COLLECTION_NAME).document(ticker)

                # For batch adds, we'll just set without checking if exists
                # (batch reads are not supported, so we can't check efficiently)
                batch.set(doc_ref, {
                    "ticker": ticker,
                    "first_detected": now,
                    "last_checked": now,
                    "error_type": error_type,
                    "retry_after": retry_after,
                    "failure_count": 1,
                }, merge=True)  # merge=True will update if exists

                operations += 1

                # Commit every 500 operations (Firestore limit)
                if operations >= 500:
                    batch.commit()
                    logger.info(f"Committed {operations} blacklist entries")
                    batch = self.db.batch()
                    operations = 0

                # Update in-memory cache
                if self._cache is not None:
                    self._cache.add(ticker)

            # Commit remaining operations
            if operations > 0:
                batch.commit()
                logger.info(f"Committed final {operations} blacklist entries")

            logger.info(
                f"Added {len(tickers)} tickers to blacklist "
                f"(error: {error_type})"
            )

        except Exception as e:
            logger.error(f"Error batch adding tickers to blacklist: {e}")

    def get_blacklisted_tickers(self) -> Set[str]:
        """
        Get set of all currently blacklisted tickers.

        Returns:
            Set of ticker symbols that should be skipped
        """
        if not self._cache_loaded:
            self._load_cache()

        return self._cache.copy()

    def remove_from_blacklist(self, ticker: str) -> None:
        """
        Remove a ticker from the blacklist (manual override).

        Args:
            ticker: Stock ticker symbol to remove
        """
        ticker = ticker.upper()

        try:
            self.db.collection(self.COLLECTION_NAME).document(ticker).delete()
            logger.info(f"Removed {ticker} from blacklist")

            # Update in-memory cache
            if self._cache is not None:
                self._cache.discard(ticker)

        except Exception as e:
            logger.error(f"Error removing {ticker} from blacklist: {e}")

    def cleanup_expired_entries(self) -> int:
        """
        Remove expired blacklist entries (past retry_after date).

        This should be run periodically to allow retrying previously
        blacklisted tickers that may have been relisted.

        Returns:
            Number of entries removed
        """
        try:
            now = datetime.now(timezone.utc)

            # Query for expired entries
            expired_docs = (
                self.db.collection(self.COLLECTION_NAME)
                .where("retry_after", "<", now)
                .stream()
            )

            # Delete expired entries
            deleted_count = 0
            batch = self.db.batch()
            operations = 0

            for doc in expired_docs:
                batch.delete(doc.reference)
                operations += 1

                # Commit every 500 operations
                if operations >= 500:
                    batch.commit()
                    deleted_count += operations
                    batch = self.db.batch()
                    operations = 0

            # Commit remaining operations
            if operations > 0:
                batch.commit()
                deleted_count += operations

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} expired blacklist entries "
                    f"(will retry these tickers)"
                )
                # Reload cache after cleanup
                self._load_cache()

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up expired entries: {e}")
            return 0

    def get_statistics(self) -> dict:
        """
        Get statistics about the blacklist.

        Returns:
            Dict with blacklist statistics
        """
        try:
            docs = self.db.collection(self.COLLECTION_NAME).stream()

            total = 0
            error_types = {}
            total_failures = 0

            for doc in docs:
                total += 1
                data = doc.to_dict()

                error_type = data.get("error_type", "unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1

                total_failures += data.get("failure_count", 0)

            return {
                "total_blacklisted": total,
                "error_types": error_types,
                "total_failures": total_failures,
                "avg_failures_per_ticker": total_failures / total if total > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def _load_cache(self) -> None:
        """
        Load blacklist from Firestore into in-memory cache.

        Only loads tickers that haven't reached their retry_after date yet.
        """
        try:
            now = datetime.now(timezone.utc)

            # Query for active blacklist entries (not expired)
            docs = (
                self.db.collection(self.COLLECTION_NAME)
                .where("retry_after", ">", now)
                .stream()
            )

            self._cache = {doc.id.upper() for doc in docs}
            self._cache_loaded = True

            logger.info(
                f"Loaded {len(self._cache)} blacklisted tickers from Firestore"
            )

        except Exception as e:
            logger.error(f"Error loading blacklist cache: {e}")
            # Initialize empty cache on error
            self._cache = set()
            self._cache_loaded = True


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    cache = DelistedTickerCache()

    # Add the 12 tickers from the user's error report
    delisted_tickers = [
        "DMII", "DNCLY", "DNMX", "DOT", "DPDSY", "DSAC",
        "DSRNY", "DTDT", "DWWYF", "DXG", "DYBTY"
    ]

    print("\n=== Adding Delisted Tickers ===")
    cache.add_batch_to_blacklist(delisted_tickers, error_type="no_data")

    print("\n=== Checking Blacklist ===")
    for ticker in ["DMII", "AAPL", "TSLA"]:
        is_blacklisted = cache.is_blacklisted(ticker)
        print(f"{ticker}: {'BLACKLISTED' if is_blacklisted else 'OK'}")

    print("\n=== Statistics ===")
    stats = cache.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\n=== Get All Blacklisted ===")
    blacklisted = cache.get_blacklisted_tickers()
    print(f"Total: {len(blacklisted)}")
    print(f"Sample: {list(blacklisted)[:10]}")
