"""
Unit tests for the TokenBucket rate limiter.

This module tests the rate limiting functionality including:
- Token acquisition and blocking behavior
- Burst capacity handling
- Rate enforcement over time
- Thread safety
- Error handling for invalid parameters
"""

import time
import threading
import pytest
from app.services.rate_limiter import TokenBucket


class TestTokenBucketInitialization:
    """Test TokenBucket initialization and parameter validation."""

    def test_valid_initialization(self):
        """Test initialization with valid parameters."""
        bucket = TokenBucket(rate=100, capacity=20, time_unit=60)
        assert bucket.rate == 100
        assert bucket.capacity == 20
        assert bucket.tokens == 20  # Should start full
        assert bucket.time_unit == 60
        assert bucket.tokens_per_second == pytest.approx(100 / 60, rel=1e-9)

    def test_default_time_unit(self):
        """Test that time_unit defaults to 60 seconds."""
        bucket = TokenBucket(rate=100, capacity=20)
        assert bucket.time_unit == 60.0

    def test_invalid_rate(self):
        """Test that negative or zero rate raises ValueError."""
        with pytest.raises(ValueError, match="rate must be positive"):
            TokenBucket(rate=0, capacity=10)
        with pytest.raises(ValueError, match="rate must be positive"):
            TokenBucket(rate=-5, capacity=10)

    def test_invalid_capacity(self):
        """Test that negative or zero capacity raises ValueError."""
        with pytest.raises(ValueError, match="capacity must be positive"):
            TokenBucket(rate=100, capacity=0)
        with pytest.raises(ValueError, match="capacity must be positive"):
            TokenBucket(rate=100, capacity=-10)

    def test_invalid_time_unit(self):
        """Test that negative or zero time_unit raises ValueError."""
        with pytest.raises(ValueError, match="time_unit must be positive"):
            TokenBucket(rate=100, capacity=10, time_unit=0)
        with pytest.raises(ValueError, match="time_unit must be positive"):
            TokenBucket(rate=100, capacity=10, time_unit=-60)


class TestTokenBucketAcquisition:
    """Test token acquisition functionality."""

    def test_burst_acquisition(self):
        """Test that burst requests up to capacity are instant."""
        bucket = TokenBucket(rate=10, capacity=5, time_unit=1.0)
        start = time.time()

        # Acquire all tokens in burst
        for _ in range(5):
            assert bucket.acquire() is True

        elapsed = time.time() - start
        assert elapsed < 0.2, f"Burst should be instant, took {elapsed:.3f}s"

    def test_rate_limiting_after_burst(self):
        """Test that rate limiting kicks in after burst exhaustion."""
        bucket = TokenBucket(rate=10, capacity=5, time_unit=1.0)

        # Exhaust burst
        for _ in range(5):
            bucket.acquire()

        # Next acquisition should block
        start = time.time()
        bucket.acquire()
        elapsed = time.time() - start

        # Should wait ~0.1s (1 token / 10 tokens per second)
        assert 0.05 < elapsed < 0.2, f"Should wait ~0.1s, waited {elapsed:.3f}s"

    def test_non_blocking_mode(self):
        """Test non-blocking mode returns False when tokens unavailable."""
        bucket = TokenBucket(rate=1, capacity=1, time_unit=1.0)

        # Acquire the only token
        assert bucket.acquire() is True

        # Non-blocking should return False immediately
        start = time.time()
        result = bucket.acquire(blocking=False)
        elapsed = time.time() - start

        assert result is False
        assert elapsed < 0.01, "Non-blocking should return immediately"

    def test_non_blocking_mode_success(self):
        """Test non-blocking mode returns True when tokens available."""
        bucket = TokenBucket(rate=10, capacity=5, time_unit=1.0)

        # Tokens available, should succeed
        assert bucket.acquire(blocking=False) is True

    def test_multiple_token_acquisition(self):
        """Test acquiring multiple tokens at once."""
        bucket = TokenBucket(rate=10, capacity=10, time_unit=1.0)

        # Acquire 5 tokens
        assert bucket.acquire(tokens=5) is True
        assert bucket.tokens == pytest.approx(5.0, abs=0.1)

    def test_invalid_token_count(self):
        """Test that invalid token counts raise ValueError."""
        bucket = TokenBucket(rate=10, capacity=10, time_unit=1.0)

        with pytest.raises(ValueError, match="tokens must be positive"):
            bucket.acquire(tokens=0)

        with pytest.raises(ValueError, match="tokens must be positive"):
            bucket.acquire(tokens=-1)

    def test_token_count_exceeds_capacity(self):
        """Test that requesting more tokens than capacity raises ValueError."""
        bucket = TokenBucket(rate=10, capacity=5, time_unit=1.0)

        with pytest.raises(ValueError, match="Cannot acquire 10 tokens"):
            bucket.acquire(tokens=10)

    def test_timeout(self):
        """Test that timeout raises TimeoutError."""
        bucket = TokenBucket(rate=1, capacity=1, time_unit=1.0)

        # Exhaust tokens
        bucket.acquire()

        # Should timeout after 0.1s (not enough time for refill)
        with pytest.raises(TimeoutError, match="Failed to acquire"):
            bucket.acquire(timeout=0.1)


class TestTokenBucketRefill:
    """Test token refill behavior."""

    def test_token_refill_over_time(self):
        """Test that tokens refill at the correct rate."""
        bucket = TokenBucket(rate=10, capacity=10, time_unit=1.0)

        # Exhaust all tokens
        bucket.acquire(tokens=10)
        assert bucket.tokens == pytest.approx(0.0, abs=0.1)

        # Wait for refill
        time.sleep(0.5)
        bucket._refill()

        # Should have ~5 tokens (10 tokens/sec * 0.5 sec)
        assert 4.5 < bucket.tokens < 5.5, f"Expected ~5 tokens, got {bucket.tokens:.2f}"

    def test_token_refill_caps_at_capacity(self):
        """Test that tokens don't exceed capacity during refill."""
        bucket = TokenBucket(rate=100, capacity=10, time_unit=1.0)

        # Wait longer than needed to fill
        time.sleep(1.0)
        bucket._refill()

        # Should cap at capacity
        assert bucket.tokens == pytest.approx(10.0, abs=0.1)

    def test_token_refill_through_public_api(self):
        """Test that tokens become available after waiting (integration test using public API only)."""
        bucket = TokenBucket(rate=10, capacity=10, time_unit=1.0)

        # Exhaust all tokens
        assert bucket.acquire(tokens=10, blocking=False) is True
        assert bucket.acquire(blocking=False) is False  # No tokens left

        # Wait for some refill (0.5s should give ~5 tokens at 10 tokens/sec)
        time.sleep(0.5)

        # Should be able to acquire again (acquire will trigger internal refill)
        # Using blocking=False to verify tokens are actually available
        assert bucket.acquire(blocking=False) is True  # ~5 tokens refilled

        # Verify we can acquire multiple tokens after waiting more
        time.sleep(0.3)  # Another ~3 tokens
        assert bucket.acquire(tokens=3, blocking=False) is True


class TestTokenBucketThreadSafety:
    """Test thread safety of TokenBucket."""

    def test_concurrent_acquisition(self):
        """Test that concurrent acquisitions are thread-safe."""
        bucket = TokenBucket(rate=100, capacity=20, time_unit=1.0)
        successful = []
        failed = []

        def acquire_token():
            """Try to acquire a token."""
            if bucket.acquire(blocking=False):
                successful.append(1)
            else:
                failed.append(1)

        # Launch 30 threads (more than capacity)
        threads = [threading.Thread(target=acquire_token) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 20 should succeed (capacity), rest should fail
        assert len(successful) == 20
        assert len(failed) == 10

    def test_concurrent_refill(self):
        """Test that refill is thread-safe."""
        bucket = TokenBucket(rate=10, capacity=10, time_unit=1.0)

        # Exhaust tokens
        bucket.acquire(tokens=10)

        # Multiple threads calling refill simultaneously
        time.sleep(0.5)
        threads = [threading.Thread(target=bucket._refill) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have correct token count (not over-counted)
        assert bucket.tokens <= bucket.capacity


class TestTokenBucketPerformance:
    """Test performance characteristics."""

    def test_high_frequency_bursts(self):
        """Test performance with high-frequency bursts."""
        bucket = TokenBucket(rate=100, capacity=20, time_unit=60.0)

        start = time.time()
        successful = 0

        for _ in range(20):
            if bucket.acquire(blocking=False):
                successful += 1

        elapsed = time.time() - start

        assert successful == 20
        assert elapsed < 0.1, f"Burst acquisition should be fast, took {elapsed*1000:.1f}ms"

    def test_sustained_load(self):
        """Test sustained load with rate limiting."""
        bucket = TokenBucket(rate=60, capacity=10, time_unit=60.0)

        successful = 0
        failed = 0

        for _ in range(15):
            if bucket.acquire(blocking=False):
                successful += 1
            else:
                failed += 1

        # First 10 should succeed (burst), next 5 should fail
        assert successful == 10
        assert failed == 5


class TestTokenBucketEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_fractional_rate(self):
        """Test that fractional rates work correctly."""
        bucket = TokenBucket(rate=0.5, capacity=1, time_unit=1.0)
        assert bucket.tokens_per_second == pytest.approx(0.5)

    def test_large_capacity(self):
        """Test with large capacity values."""
        bucket = TokenBucket(rate=10000, capacity=1000, time_unit=60.0)
        assert bucket.acquire(tokens=1000) is True

    def test_very_small_time_unit(self):
        """Test with very small time units."""
        bucket = TokenBucket(rate=10, capacity=5, time_unit=0.1)
        assert bucket.tokens_per_second == pytest.approx(100.0)
