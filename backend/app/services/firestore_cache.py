"""
Firestore Cache Service for Screener Results

Provides functions to read cached screener results from Firestore.
Batch jobs write to Firestore daily, API reads from cache for fast responses.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)


class FirestoreCache:
    """Service for reading cached screener results from Firestore."""

    def __init__(self):
        """Initialize Firestore client."""
        try:
            self.db = firestore.Client()
            logger.info("Firestore client initialized for cache reading")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            self.db = None

    def get_screener_results(
        self,
        screener_name: str,
        date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached screener results from Firestore.

        Args:
            screener_name: Name of screener (undiscovered, coiled_spring, smart_money)
            date: Date string (YYYY-MM-DD). If None, uses today.

        Returns:
            Dict with screener results if found, None if not found or error

        Example:
            >>> cache = FirestoreCache()
            >>> results = cache.get_screener_results("coiled_spring", "2025-11-16")
            >>> if results:
            ...     print(f"Found {results['total_count']} stocks")
        """
        if not self.db:
            logger.warning("Firestore client not available")
            return None

        try:
            # Use today's date if not specified
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")

            # Document path: screeners/{screener_name}/runs/{date}
            doc_ref = (
                self.db
                .collection("screeners")
                .document(screener_name)
                .collection("runs")
                .document(date)
            )

            # Get document
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                logger.info(
                    f"✓ Cache HIT: screeners/{screener_name}/runs/{date} "
                    f"({data.get('total_count', 0)} results)"
                )
                return data
            else:
                logger.info(f"✗ Cache MISS: screeners/{screener_name}/runs/{date}")
                return None

        except Exception as e:
            logger.error(f"Error reading from Firestore cache: {e}")
            return None

    def get_latest_run(self, screener_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent screener run (any date).

        Args:
            screener_name: Name of screener

        Returns:
            Dict with screener results if found, None if not found

        Example:
            >>> cache = FirestoreCache()
            >>> results = cache.get_latest_run("coiled_spring")
        """
        if not self.db:
            logger.warning("Firestore client not available")
            return None

        try:
            # Query for most recent run
            docs = (
                self.db
                .collection("screeners")
                .document(screener_name)
                .collection("runs")
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(1)
                .stream()
            )

            for doc in docs:
                data = doc.to_dict()
                logger.info(
                    f"✓ Found latest run: screeners/{screener_name}/runs/{doc.id} "
                    f"({data.get('total_count', 0)} results)"
                )
                return data

            logger.info(f"✗ No runs found for screener: {screener_name}")
            return None

        except Exception as e:
            logger.error(f"Error getting latest run from Firestore: {e}")
            return None
