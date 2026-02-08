"""Redis-backed rate limiting."""

import time
from typing import Protocol


class CacheProtocol(Protocol):
    """Protocol for cache interface."""

    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl: int | None = None) -> None: ...
    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, ttl: int) -> None: ...


class RateLimiter:
    """Sliding window rate limiter using Redis."""

    def __init__(
        self,
        cache: CacheProtocol,
        max_requests: int,
        window_seconds: int,
        key_prefix: str = "ratelimit",
    ):
        """Initialize rate limiter.

        Args:
            cache: Cache service implementing CacheProtocol
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            key_prefix: Prefix for rate limit keys
        """
        self.cache = cache
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    def _get_key(self, identifier: str) -> str:
        """Get rate limit key for an identifier."""
        window = int(time.time()) // self.window_seconds
        return f"{self.key_prefix}:{identifier}:{window}"

    async def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """Check if request is allowed under rate limit.

        Args:
            identifier: Unique identifier (e.g., IP address, API key)

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        key = self._get_key(identifier)

        try:
            current = await self.cache.incr(key)
            if current == 1:
                await self.cache.expire(key, self.window_seconds)

            remaining = max(0, self.max_requests - current)
            allowed = current <= self.max_requests

            return allowed, remaining
        except Exception:
            # If rate limiting fails, allow the request
            return True, self.max_requests

    async def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for an identifier.

        Args:
            identifier: Unique identifier

        Returns:
            Number of remaining requests
        """
        key = self._get_key(identifier)

        try:
            current_str = await self.cache.get(key)
            if current_str is None:
                return self.max_requests
            current = int(current_str)
            return max(0, self.max_requests - current)
        except Exception:
            return self.max_requests
