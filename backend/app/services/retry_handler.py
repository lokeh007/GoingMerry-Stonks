"""
Retry Handler with Exponential Backoff and Jitter.

This module provides a decorator for retrying failed API calls with
intelligent backoff strategies to handle rate limiting gracefully.
"""

import logging
import time
import random
from typing import Callable, TypeVar, Any, Tuple, Type
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def exponential_backoff_with_jitter(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that retries a function with exponential backoff and jitter.

    This implements the "Full Jitter" strategy from AWS Architecture Blog:
    https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

    Retry delay calculation:
    - Without jitter: delay = min(max_delay, base_delay * (exponential_base ** attempt))
    - With full jitter: delay = random.uniform(0, min(max_delay, base_delay * (exponential_base ** attempt)))

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds before exponential growth (default: 1.0)
        max_delay: Maximum delay in seconds to cap exponential growth (default: 60.0)
        exponential_base: Base for exponential growth (default: 2.0)
        jitter: Whether to add randomness to delay (default: True)
        exceptions: Tuple of exception types to catch and retry (default: all exceptions)

    Returns:
        Decorated function that retries on failure

    Example:
        >>> @exponential_backoff_with_jitter(max_retries=5, base_delay=2.0)
        ... def fetch_data(ticker: str):
        ...     return api.get(ticker)
        >>>
        >>> # Retry schedule with jitter (random between 0 and max):
        >>> # Attempt 1: Immediate
        >>> # Attempt 2: 0-2 seconds (base_delay * 2^0)
        >>> # Attempt 3: 0-4 seconds (base_delay * 2^1)
        >>> # Attempt 4: 0-8 seconds (base_delay * 2^2)
        >>> # Attempt 5: 0-16 seconds (base_delay * 2^3)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    # Don't retry on last attempt
                    if attempt >= max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise

                    # Calculate exponential delay
                    exponential_delay = base_delay * (exponential_base ** attempt)
                    capped_delay = min(max_delay, exponential_delay)

                    # Add jitter (full jitter strategy - random between 0 and capped_delay)
                    if jitter:
                        delay = random.uniform(0, capped_delay)
                    else:
                        delay = capped_delay

                    # Check if this is a rate limit error
                    error_msg = str(e).lower()
                    is_rate_limit = (
                        'rate limit' in error_msg or
                        'too many requests' in error_msg or
                        '429' in error_msg or
                        'throttle' in error_msg or
                        'throttled' in error_msg
                    )

                    if is_rate_limit:
                        logger.warning(
                            f"Rate limit detected in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): "
                            f"{e}. Retrying in {delay:.2f}s..."
                        )
                    else:
                        logger.warning(
                            f"Error in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): "
                            f"{e}. Retrying in {delay:.2f}s..."
                        )

                    time.sleep(delay)

            # This should never be reached due to raise in the loop, but satisfy type checker
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Function {func.__name__} failed without exception")

        return wrapper
    return decorator


def adaptive_backoff_with_jitter(
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 120.0,
    rate_limit_multiplier: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator with adaptive backoff that increases delay for rate limit errors.

    This is more aggressive than standard exponential backoff for rate limiting.
    When a rate limit error is detected, the delay is multiplied by an additional factor.

    Args:
        max_retries: Maximum number of retry attempts (default: 5)
        base_delay: Base delay in seconds (default: 2.0)
        max_delay: Maximum delay in seconds (default: 120.0 = 2 minutes)
        rate_limit_multiplier: Extra multiplier for rate limit errors (default: 2.0)

    Returns:
        Decorated function that retries on failure with adaptive backoff

    Example:
        >>> @adaptive_backoff_with_jitter(max_retries=5, base_delay=3.0)
        ... def fetch_ticker_data(ticker: str):
        ...     return yfinance.Ticker(ticker).info
        >>>
        >>> # For rate limit errors, delays are:
        >>> # Attempt 1: Immediate
        >>> # Attempt 2: 0-6 seconds (base_delay * 2 * rate_limit_multiplier)
        >>> # Attempt 3: 0-12 seconds
        >>> # Attempt 4: 0-24 seconds
        >>> # Attempt 5: 0-48 seconds
        >>> # Attempt 6: 0-96 seconds
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Don't retry on last attempt
                    if attempt >= max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise

                    # Check if this is a rate limit error
                    error_msg = str(e).lower()
                    is_rate_limit = (
                        'rate limit' in error_msg or
                        'too many requests' in error_msg or
                        '429' in error_msg or
                        'throttle' in error_msg or
                        'throttled' in error_msg or
                        'exceed' in error_msg
                    )

                    # Calculate delay with adaptive multiplier for rate limits
                    if is_rate_limit:
                        # More aggressive backoff for rate limits
                        exponential_delay = base_delay * (2 ** attempt) * rate_limit_multiplier
                    else:
                        # Standard exponential backoff for other errors
                        exponential_delay = base_delay * (2 ** attempt)

                    capped_delay = min(max_delay, exponential_delay)

                    # Add full jitter
                    delay = random.uniform(0, capped_delay)

                    if is_rate_limit:
                        logger.warning(
                            f"⚠ RATE LIMIT in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): "
                            f"{e}. Backing off for {delay:.2f}s (adaptive backoff)..."
                        )
                    else:
                        logger.warning(
                            f"Error in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): "
                            f"{e}. Retrying in {delay:.2f}s..."
                        )

                    time.sleep(delay)

            # This should never be reached due to raise in the loop, but satisfy type checker
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Function {func.__name__} failed without exception")

        return wrapper
    return decorator
