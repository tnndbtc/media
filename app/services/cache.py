"""Redis cache service."""

import json
import logging as std_logging
from typing import Any, TypeVar

import redis.asyncio as redis
import structlog
from pydantic import BaseModel

from app.utils.exceptions import CacheError

T = TypeVar("T", bound=BaseModel)


class CacheService:
    """Redis-based caching service with Pydantic model support."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        password: str | None = None,
        default_ttl: int = 3600,
        enabled: bool = True,
    ):
        """Initialize cache service.

        Args:
            redis_url: Redis connection URL
            password: Redis password (optional)
            default_ttl: Default TTL in seconds
            enabled: Whether caching is enabled
        """
        self.redis_url = redis_url
        self.password = password
        self.default_ttl = default_ttl
        self.enabled = enabled
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                password=self.password,
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.warning("redis_ping_failed", error=str(e))
            raise CacheError(f"Redis ping failed: {e}")

    async def get(self, key: str) -> str | None:
        """Get raw string value from cache."""
        if not self.enabled:
            return None

        try:
            return await self.client.get(key)
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> None:
        """Set raw string value in cache."""
        if not self.enabled:
            return

        try:
            await self.client.set(key, value, ex=ttl or self.default_ttl)
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Get JSON value from cache."""
        raw = await self.get(key)
        if raw is None:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("cache_json_decode_failed", key=key, error=str(e))
            return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Set JSON value in cache."""
        try:
            json_str = json.dumps(value, default=str)
            await self.set(key, json_str, ttl)
        except Exception as e:
            logger.warning("cache_json_encode_failed", key=key, error=str(e))

    async def get_model(self, key: str, model_class: type[T]) -> T | None:
        """Get Pydantic model from cache."""
        data = await self.get_json(key)
        if data is None:
            return None

        try:
            return model_class.model_validate(data)
        except Exception as e:
            logger.warning("cache_model_validation_failed", key=key, error=str(e))
            return None

    async def set_model(
        self,
        key: str,
        model: BaseModel,
        ttl: int | None = None,
    ) -> None:
        """Set Pydantic model in cache."""
        await self.set_json(key, model.model_dump(mode="json"), ttl)

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self.enabled:
            return False

        try:
            result = await self.client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning("cache_delete_failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.enabled:
            return False

        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.warning("cache_exists_failed", key=key, error=str(e))
            return False

    async def incr(self, key: str) -> int:
        """Increment a counter."""
        try:
            return await self.client.incr(key)
        except Exception as e:
            logger.warning("cache_incr_failed", key=key, error=str(e))
            raise CacheError(f"Cache increment failed: {e}")

    async def expire(self, key: str, ttl: int) -> None:
        """Set expiration on a key."""
        try:
            await self.client.expire(key, ttl)
        except Exception as e:
            logger.warning("cache_expire_failed", key=key, error=str(e))

    async def get_or_set(
        self,
        key: str,
        factory: Any,
        ttl: int | None = None,
    ) -> dict[str, Any] | None:
        """Get from cache or compute and store.

        Args:
            key: Cache key
            factory: Async callable that returns the value
            ttl: Time to live in seconds

        Returns:
            Cached or computed value
        """
        cached = await self.get_json(key)
        if cached is not None:
            ctx = structlog.contextvars.get_contextvars()
            request_id = ctx.get("request_id", "unknown")
            std_logging.debug(f"cache_hit - {key} [request_id: {request_id}]")
            return cached

        ctx = structlog.contextvars.get_contextvars()
        request_id = ctx.get("request_id", "unknown")
        std_logging.debug(f"cache_miss - {key} [request_id: {request_id}]")
        value = await factory()
        if value is not None:
            await self.set_json(key, value, ttl)
        return value
