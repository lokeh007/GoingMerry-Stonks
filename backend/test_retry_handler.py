#!/usr/bin/env python3
"""
Test script for retry handler with exponential backoff and jitter.

This script verifies that the retry decorator works correctly with simulated
rate limit errors.
"""

import time
from app.services.retry_handler import adaptive_backoff_with_jitter, exponential_backoff_with_jitter


class SimulatedRateLimitError(Exception):
    """Simulated rate limit error for testing."""
    pass


# Test 1: Adaptive backoff with simulated failures
attempt_count = 0


@adaptive_backoff_with_jitter(max_retries=3, base_delay=0.5, max_delay=10.0)
def failing_function_with_rate_limit():
    """Function that fails with rate limit error the first 2 times."""
    global attempt_count
    attempt_count += 1
    print(f"Attempt {attempt_count}")

    if attempt_count < 3:
        raise SimulatedRateLimitError("429 Too Many Requests - Rate limit exceeded")

    return "Success!"


# Test 2: Standard exponential backoff
attempt_count_2 = 0


@exponential_backoff_with_jitter(max_retries=4, base_delay=0.5, max_delay=10.0)
def failing_function_standard():
    """Function that fails with generic error the first 3 times."""
    global attempt_count_2
    attempt_count_2 += 1
    print(f"Standard backoff attempt {attempt_count_2}")

    if attempt_count_2 < 4:
        raise Exception("Temporary error")

    return "Standard success!"


def main():
    """Run retry handler tests."""
    print("=" * 80)
    print("Testing Adaptive Backoff with Rate Limit Detection")
    print("=" * 80)

    try:
        start = time.time()
        result = failing_function_with_rate_limit()
        elapsed = time.time() - start
        print(f"✓ Result: {result}")
        print(f"⏱  Time elapsed: {elapsed:.2f}s")
        print(f"✓ Total attempts: {attempt_count}")
    except Exception as e:
        print(f"✗ Failed: {e}")

    print()
    print("=" * 80)
    print("Testing Standard Exponential Backoff")
    print("=" * 80)

    try:
        start = time.time()
        result = failing_function_standard()
        elapsed = time.time() - start
        print(f"✓ Result: {result}")
        print(f"⏱  Time elapsed: {elapsed:.2f}s")
        print(f"✓ Total attempts: {attempt_count_2}")
    except Exception as e:
        print(f"✗ Failed: {e}")

    print()
    print("=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
