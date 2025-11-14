"""
Rate Limiting Module.

This module provides thread-safe rate limiting utilities for API clients.
Implements the token bucket algorithm for flexible rate limiting with burst support.

The TokenBucket class can be used by any service that needs to enforce rate limits,
making it reusable across multiple API providers.
"""

import logging
import time
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Thread-safe token bucket rate limiter.

    Allows burst requests up to bucket capacity while maintaining
    an average rate. More flexible than simple interval-based limiting.

    Example:
        # Allow 100 requests per minute with burst capacity of 20
        limiter = TokenBucket(rate=100, capacity=20, time_unit=60)
        limiter.acquire()  # Blocks if no tokens available
    """

    def __init__(self, rate: float, capacity: int, time_unit: float = 60.0):
        """
        Initialize token bucket.

        Args:
            rate: Number of tokens to add per time_unit (e.g., 100 = 100 requests/min)
            capacity: Maximum bucket capacity (burst size) - integer representing max requests
            time_unit: Time window in seconds (default: 60 = 1 minute)

        Raises:
            ValueError: If rate, capacity, or time_unit are not positive

        Note:
            Internal token count (self.tokens) is stored as float for precise refill
            calculations, but capacity should be an integer representing discrete API calls.
        """
        # Validate parameters
        if rate <= 0:
            raise ValueError(f"rate must be positive, got {rate}")
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        if time_unit <= 0:
            raise ValueError(f"time_unit must be positive, got {time_unit}")

        self.rate = rate  # tokens per time_unit
        self.capacity = capacity  # max tokens
        self.tokens = capacity  # start full
        self.time_unit = time_unit
        self.lock = threading.Lock()
        self.last_update = time.time()

        # Calculate token refill rate per second
        self.tokens_per_second = rate / time_unit

        logger.info(
            f"TokenBucket initialized: {rate} req/{time_unit}s, "
            f"capacity={capacity}, refill={self.tokens_per_second:.2f} tokens/sec"
        )

    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last update."""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.tokens_per_second
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_update = now

    def acquire(self, tokens: int = 1, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire (default: 1)
            blocking: If True, wait for tokens. If False, return immediately (default: True)
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if tokens acquired, False if not available (non-blocking mode only)

        Raises:
            ValueError: If tokens is not positive or exceeds capacity
            TimeoutError: If timeout exceeded while waiting for tokens
        """
        # Validate tokens parameter
        if tokens <= 0:
            raise ValueError(f"tokens must be positive, got {tokens}")
        if tokens > self.capacity:
            raise ValueError(
                f"Cannot acquire {tokens} tokens (bucket capacity is {self.capacity})"
            )

        start_time = time.time()

        while True:
            with self.lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    logger.debug(f"Acquired {tokens} token(s), {self.tokens:.1f} remaining")
                    return True

                if not blocking:
                    logger.debug(f"Tokens not available ({self.tokens:.1f} < {tokens})")
                    return False

                # Calculate sleep time until next token available
                tokens_needed = tokens - self.tokens
                sleep_time = tokens_needed / self.tokens_per_second

                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        raise TimeoutError(f"Failed to acquire {tokens} tokens within {timeout}s")
                    sleep_time = min(sleep_time, timeout - elapsed)

            logger.debug(f"Waiting {sleep_time:.2f}s for {tokens} token(s)")
            time.sleep(min(sleep_time, 0.1))  # Sleep max 100ms at a time
