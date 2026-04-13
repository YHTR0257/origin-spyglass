import time

from spyglass_utils.rate_limiter import RateLimiter


def test_allows_within_limit() -> None:
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.is_allowed("key") is True
    assert limiter.is_allowed("key") is True
    assert limiter.is_allowed("key") is True


def test_blocks_over_limit() -> None:
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.is_allowed("key")
    assert limiter.is_allowed("key") is False


def test_keys_are_independent() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.is_allowed("key_a") is True
    assert limiter.is_allowed("key_b") is True
    assert limiter.is_allowed("key_a") is False


def test_window_expiry() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=0.05)
    assert limiter.is_allowed("key") is True
    assert limiter.is_allowed("key") is False
    time.sleep(0.1)
    assert limiter.is_allowed("key") is True
