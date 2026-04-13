import threading
import time
from collections import defaultdict


class RateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            cutoff = now - self.window_seconds
            self._timestamps[key] = [t for t in self._timestamps[key] if t > cutoff]
            if len(self._timestamps[key]) >= self.max_requests:
                return False
            self._timestamps[key].append(now)
            return True


# Singleton: 60 requests per minute per IP
chat_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
