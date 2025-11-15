#!/usr/bin/env python3
"""
Test script for retry handler with exponential backoff and jitter.

This script verifies that the retry decorator works correctly with simulated
rate limit errors using class-based test functions for better reusability.
"""

import time
from app.services.retry_handler import adaptive_backoff_with_jitter, exponential_backoff_with_jitter


class SimulatedRateLimitError(Exception):
    """Simulated rate limit error for testing."""
    pass


class RetryHandlerTests:
    """Test suite for retry handler decorators."""

    def __init__(self):
        """Initialize test suite."""
        self.results = []

    def _create_failing_function_with_rate_limit(self, fail_count: int):
        """
        Create a function that fails with rate limit error a specified number of times.

        Args:
            fail_count: Number of times the function should fail before succeeding

        Returns:
            Tuple of (decorated function, attempt counter closure)
        """
        attempts = {"count": 0}

        @adaptive_backoff_with_jitter(max_retries=fail_count + 1, base_delay=0.5, max_delay=10.0)
        def failing_function():
            """Function that fails with rate limit error."""
            attempts["count"] += 1
            print(f"  Attempt {attempts['count']}")

            if attempts["count"] <= fail_count:
                raise SimulatedRateLimitError("429 Too Many Requests - Rate limit exceeded")

            return "Success!"

        return failing_function, attempts

    def _create_failing_function_standard(self, fail_count: int):
        """
        Create a function that fails with generic error a specified number of times.

        Args:
            fail_count: Number of times the function should fail before succeeding

        Returns:
            Tuple of (decorated function, attempt counter closure)
        """
        attempts = {"count": 0}

        @exponential_backoff_with_jitter(max_retries=fail_count + 1, base_delay=0.5, max_delay=10.0)
        def failing_function():
            """Function that fails with generic transient error."""
            attempts["count"] += 1
            print(f"  Standard backoff attempt {attempts['count']}")

            if attempts["count"] <= fail_count:
                raise ConnectionError("Temporary connection error")

            return "Standard success!"

        return failing_function, attempts

    def _create_non_retryable_function(self):
        """
        Create a function that raises a non-retryable error.

        Returns:
            Tuple of (decorated function, attempt counter closure)
        """
        attempts = {"count": 0}

        @adaptive_backoff_with_jitter(max_retries=3, base_delay=0.5, max_delay=10.0)
        def failing_function():
            """Function that raises a non-retryable error."""
            attempts["count"] += 1
            print(f"  Attempt {attempts['count']}")
            raise ValueError("Invalid ticker - non-retryable error")

        return failing_function, attempts

    def test_adaptive_backoff_with_rate_limit(self):
        """Test adaptive backoff with rate limit detection."""
        print("=" * 80)
        print("Test 1: Adaptive Backoff with Rate Limit Detection")
        print("=" * 80)

        failing_function, attempts = self._create_failing_function_with_rate_limit(fail_count=2)

        try:
            start = time.time()
            result = failing_function()
            elapsed = time.time() - start

            print(f"✓ Result: {result}")
            print(f"⏱  Time elapsed: {elapsed:.2f}s")
            print(f"✓ Total attempts: {attempts['count']}")
            print(f"✓ Test PASSED: Function succeeded after {attempts['count']} attempts")

            self.results.append(("Adaptive Backoff (Rate Limit)", "PASSED"))
        except Exception as e:
            print(f"✗ Failed: {e}")
            self.results.append(("Adaptive Backoff (Rate Limit)", "FAILED"))

    def test_standard_exponential_backoff(self):
        """Test standard exponential backoff."""
        print()
        print("=" * 80)
        print("Test 2: Standard Exponential Backoff")
        print("=" * 80)

        failing_function, attempts = self._create_failing_function_standard(fail_count=3)

        try:
            start = time.time()
            result = failing_function()
            elapsed = time.time() - start

            print(f"✓ Result: {result}")
            print(f"⏱  Time elapsed: {elapsed:.2f}s")
            print(f"✓ Total attempts: {attempts['count']}")
            print(f"✓ Test PASSED: Function succeeded after {attempts['count']} attempts")

            self.results.append(("Standard Exponential Backoff", "PASSED"))
        except Exception as e:
            print(f"✗ Failed: {e}")
            self.results.append(("Standard Exponential Backoff", "FAILED"))

    def test_non_retryable_error(self):
        """Test that non-retryable errors fail immediately."""
        print()
        print("=" * 80)
        print("Test 3: Non-Retryable Error (Should Fail Immediately)")
        print("=" * 80)

        failing_function, attempts = self._create_non_retryable_function()

        try:
            start = time.time()
            result = failing_function()
            elapsed = time.time() - start

            print(f"✗ Test FAILED: Function should have failed immediately but succeeded")
            print(f"  Result: {result}")
            print(f"  Attempts: {attempts['count']}")

            self.results.append(("Non-Retryable Error", "FAILED"))
        except ValueError as e:
            elapsed = time.time() - start

            # Should fail on first attempt with minimal delay
            if attempts['count'] == 1 and elapsed < 1.0:
                print(f"✓ Error (as expected): {e}")
                print(f"✓ Total attempts: {attempts['count']}")
                print(f"⏱  Time elapsed: {elapsed:.2f}s")
                print(f"✓ Test PASSED: Non-retryable error failed immediately")

                self.results.append(("Non-Retryable Error", "PASSED"))
            else:
                print(f"✗ Test FAILED: Error failed but with wrong behavior")
                print(f"  Attempts: {attempts['count']} (expected: 1)")
                print(f"  Elapsed: {elapsed:.2f}s (expected: < 1.0s)")

                self.results.append(("Non-Retryable Error", "FAILED"))

    def run_all_tests(self):
        """Run all tests and print summary."""
        self.test_adaptive_backoff_with_rate_limit()
        self.test_standard_exponential_backoff()
        self.test_non_retryable_error()

        print()
        print("=" * 80)
        print("Test Summary")
        print("=" * 80)

        for test_name, status in self.results:
            status_symbol = "✓" if status == "PASSED" else "✗"
            print(f"{status_symbol} {test_name}: {status}")

        print()
        passed = sum(1 for _, status in self.results if status == "PASSED")
        total = len(self.results)
        print(f"Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests PASSED!")
        else:
            print(f"⚠️  {total - passed} test(s) FAILED")

        print("=" * 80)

        return passed == total


def main():
    """Run retry handler tests."""
    tests = RetryHandlerTests()
    success = tests.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
