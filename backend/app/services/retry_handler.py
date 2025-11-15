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


# Transient errors that should be retried
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,  # Includes network-related errors
)


def is_rate_limit_error(error: Exception) -> bool:
    """
    Check if an error is a rate limit error.

    This function detects rate limiting errors by checking the error message
    for common rate limit indicators.

    Args:
        error: Exception to check

    Returns:
        True if the error appears to be a rate limit error, False otherwise

    Example:
        >>> err = Exception("429 Too Many Requests")
        >>> is_rate_limit_error(err)
        True
        >>> err = Exception("Invalid ticker")
        >>> is_rate_limit_error(err)
        False
    """
    error_msg = str(error).lower()
    return any([
        'rate limit' in error_msg,
        'too many requests' in error_msg,
        '429' in error_msg,
        'throttle' in error_msg,
        'throttled' in error_msg,
        'exceed' in error_msg,
    ])


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error should be retried.

    Only transient errors (network issues, rate limits, timeouts) should be retried.
    Permanent errors (invalid input, authentication, not found) should fail immediately.

    Args:
        error: Exception to check

    Returns:
        True if the error should be retried, False otherwise

    Example:
        >>> is_retryable_error(TimeoutError("Connection timeout"))
        True
        >>> is_retryable_error(ValueError("Invalid ticker"))
        False
    """
    # Check for known retryable exception types
    if isinstance(error, RETRYABLE_EXCEPTIONS):
        return True

    # Check for rate limit errors (even if generic Exception)
    if is_rate_limit_error(error):
        return True

    # Check for other transient error indicators
    error_msg = str(error).lower()
    transient_indicators = [
        'timeout',
        'connection',
        'network',
        '503',  # Service Unavailable
        '502',  # Bad Gateway
        '504',  # Gateway Timeout
        'temporarily unavailable',
        'try again',
    ]

    return any(indicator in error_msg for indicator in transient_indicators)


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

    Only retries on transient errors (network issues, timeouts, rate limits).
    Permanent errors (invalid input, authentication failures) fail immediately.

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
        >>> # Retry schedule with jitter (delays occur AFTER each failed attempt):
        >>> # Attempt 1: Immediate (no delay before first attempt)
        >>> # After failure -> Wait 0-2 seconds, then Attempt 2 (base_delay * 2^0 = 2.0)
        >>> # After failure -> Wait 0-4 seconds, then Attempt 3 (base_delay * 2^1 = 4.0)
        >>> # After failure -> Wait 0-8 seconds, then Attempt 4 (base_delay * 2^2 = 8.0)
        >>> # After failure -> Wait 0-16 seconds, then Attempt 5 (base_delay * 2^3 = 16.0)
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

                    # Check if error should be retried
                    if not is_retryable_error(e):
                        logger.warning(
                            f"Non-retryable error in {func.__name__}: {e}. Failing immediately."
                        )
                        raise

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

                    # Use helper function for rate limit detection
                    if is_rate_limit_error(e):
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

    Only retries on transient errors (network issues, timeouts, rate limits).
    Permanent errors (invalid input, authentication failures) fail immediately.

    Args:
        max_retries: Maximum number of retry attempts (default: 5)
        base_delay: Base delay in seconds (default: 2.0)
        max_delay: Maximum delay in seconds (default: 120.0 = 2 minutes)
        rate_limit_multiplier: Extra multiplier for rate limit errors (default: 2.0)

    Returns:
        Decorated function that retries on failure with adaptive backoff

    Example:
        >>> @adaptive_backoff_with_jitter(max_retries=5, base_delay=3.0, rate_limit_multiplier=2.0)
        ... def fetch_ticker_data(ticker: str):
        ...     return yfinance.Ticker(ticker).info
        >>>
        >>> # For rate limit errors, delays are (delays occur AFTER each failed attempt):
        >>> # Attempt 1: Immediate (no delay before first attempt)
        >>> # After failure -> Wait 0-12 seconds, then Attempt 2 (3.0 * 2^0 * 2.0 = 6.0)
        >>> # After failure -> Wait 0-24 seconds, then Attempt 3 (3.0 * 2^1 * 2.0 = 12.0)
        >>> # After failure -> Wait 0-48 seconds, then Attempt 4 (3.0 * 2^2 * 2.0 = 24.0)
        >>> # After failure -> Wait 0-96 seconds, then Attempt 5 (3.0 * 2^3 * 2.0 = 48.0)
        >>> # After failure -> Wait 0-120 seconds, then Attempt 6 (capped at max_delay=120.0)
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

                    # Check if error should be retried
                    if not is_retryable_error(e):
                        logger.warning(
                            f"Non-retryable error in {func.__name__}: {e}. Failing immediately."
                        )
                        raise

                    # Don't retry on last attempt
                    if attempt >= max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise

                    # Use helper function for rate limit detection
                    rate_limited = is_rate_limit_error(e)

                    # Calculate delay with adaptive multiplier for rate limits
                    if rate_limited:
                        # More aggressive backoff for rate limits
                        exponential_delay = base_delay * (2 ** attempt) * rate_limit_multiplier
                    else:
                        # Standard exponential backoff for other errors
                        exponential_delay = base_delay * (2 ** attempt)

                    capped_delay = min(max_delay, exponential_delay)

                    # Add full jitter
                    delay = random.uniform(0, capped_delay)

                    if rate_limited:
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
