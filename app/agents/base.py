"""Base agent class for all AI agents."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from app.services.cache import CacheService
from app.utils.hashing import generate_cache_key
from app.utils.logging import get_logger

logger = get_logger(__name__)

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Abstract base class for AI agents.

    Provides common functionality like caching, logging, and error handling.
    """

    # Agent name for logging and caching
    name: str = "base_agent"

    # Whether to cache results
    cache_enabled: bool = True

    # Cache TTL in seconds
    cache_ttl: int = 3600

    def __init__(self, cache: CacheService | None = None):
        """Initialize the agent.

        Args:
            cache: Optional cache service for result caching
        """
        self.cache = cache
        self.logger = get_logger(f"agent.{self.name}")
        self._last_cache_hit: bool = False

    @abstractmethod
    async def process(self, input_data: InputT) -> OutputT:
        """Process input and return output.

        This is the main method that subclasses must implement.

        Args:
            input_data: Input data for processing

        Returns:
            Processed output
        """
        pass

    def _get_cache_key(self, input_data: InputT) -> str:
        """Generate cache key for input data.

        Override this method to customize cache key generation.

        Args:
            input_data: Input data

        Returns:
            Cache key string
        """
        return generate_cache_key(self.name, input_data)

    async def execute(self, input_data: InputT) -> OutputT:
        """Execute the agent with caching and logging.

        This is the public method that should be called to run the agent.

        Args:
            input_data: Input data for processing

        Returns:
            Processed output (from cache or fresh processing)
        """
        self.logger.info("agent_execute_start", input_type=type(input_data).__name__)
        self._last_cache_hit = False

        # Check cache
        if self.cache_enabled and self.cache:
            cache_key = self._get_cache_key(input_data)
            cached = await self._get_from_cache(cache_key)
            if cached is not None:
                self.logger.info("agent_cache_hit", cache_key=cache_key)
                self._last_cache_hit = True
                return cached

        # Process
        try:
            result = await self.process(input_data)
            self.logger.info("agent_execute_success")

            # Cache result
            if self.cache_enabled and self.cache:
                await self._set_in_cache(cache_key, result)

            return result

        except Exception as e:
            self.logger.error("agent_execute_error", error=str(e))
            raise

    async def _get_from_cache(self, key: str) -> OutputT | None:
        """Get result from cache.

        Override to customize cache retrieval for specific output types.

        Args:
            key: Cache key

        Returns:
            Cached result or None
        """
        if not self.cache:
            return None

        data = await self.cache.get_json(key)
        if data is not None:
            return self._deserialize_output(data)
        return None

    async def _set_in_cache(self, key: str, result: OutputT) -> None:
        """Store result in cache.

        Override to customize cache storage for specific output types.

        Args:
            key: Cache key
            result: Result to cache
        """
        if not self.cache:
            return

        data = self._serialize_output(result)
        await self.cache.set_json(key, data, ttl=self.cache_ttl)

    def _serialize_output(self, output: OutputT) -> dict[str, Any]:
        """Serialize output for caching.

        Override for custom serialization.

        Args:
            output: Output to serialize

        Returns:
            Serializable dictionary
        """
        if hasattr(output, "model_dump"):
            return output.model_dump(mode="json")
        return {"data": output}

    def _deserialize_output(self, data: dict[str, Any]) -> OutputT:
        """Deserialize output from cache.

        Override for custom deserialization.

        Args:
            data: Cached data

        Returns:
            Deserialized output
        """
        # Default implementation returns raw data
        # Subclasses should override for proper model reconstruction
        return data  # type: ignore
