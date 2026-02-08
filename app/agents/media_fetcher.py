"""Media fetcher agent for parallel API queries."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.agents.base import BaseAgent
from app.models.media import MediaItem, MediaType
from app.models.query import GeneratedQuery
from app.services.cache import CacheService
from app.services.pexels import PexelsClient
from app.services.pixabay import PixabayClient


@dataclass
class FetchInput:
    """Input for media fetching."""

    query: GeneratedQuery
    media_types: list[MediaType]
    limit: int = 20
    include_sources: list[str] | None = None
    safe_search: bool = True


@dataclass
class FetchResult:
    """Result from media fetching."""

    items: list[MediaItem] = field(default_factory=list)
    total_found: int = 0
    sources_queried: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class MediaFetcherAgent(BaseAgent[FetchInput, FetchResult]):
    """Agent for fetching media from multiple sources in parallel.

    Queries Pexels and Pixabay APIs concurrently and aggregates results.
    """

    name = "media_fetcher"
    cache_enabled = True
    cache_ttl = 1800  # Cache for 30 minutes

    def __init__(
        self,
        pexels_client: PexelsClient,
        pixabay_client: PixabayClient,
        cache: CacheService | None = None,
    ):
        """Initialize media fetcher.

        Args:
            pexels_client: Pexels API client
            pixabay_client: Pixabay API client
            cache: Optional cache service
        """
        super().__init__(cache)
        self.pexels_client = pexels_client
        self.pixabay_client = pixabay_client

    def _get_cache_key(self, input_data: FetchInput) -> str:
        """Generate cache key from fetch input."""
        from app.utils.hashing import generate_cache_key

        return generate_cache_key(
            self.name,
            input_data.query.english_query,
            [mt.value for mt in input_data.media_types],
            input_data.limit,
            input_data.include_sources,
        )

    async def process(self, input_data: FetchInput) -> FetchResult:
        """Fetch media from all sources in parallel.

        Args:
            input_data: Fetch parameters

        Returns:
            FetchResult with aggregated items
        """
        result = FetchResult()
        tasks = []
        sources = []

        # Determine which sources to query
        include_pexels = input_data.include_sources is None or "pexels" in input_data.include_sources
        include_pixabay = (
            input_data.include_sources is None or "pixabay" in input_data.include_sources
        )

        # Calculate per-source limit
        source_count = sum([include_pexels, include_pixabay])
        per_source_limit = input_data.limit // source_count if source_count > 0 else input_data.limit

        # Create fetch tasks
        # Use bilingual keywords if available, otherwise fall back to english_query
        if input_data.query.bilingual_keywords:
            search_query = " ".join(input_data.query.bilingual_keywords[:6])  # Limit to 6 keywords
        else:
            search_query = input_data.query.english_query

        if include_pexels:
            tasks.append(self._fetch_pexels(search_query, input_data.media_types, per_source_limit))
            sources.append("pexels")

        if include_pixabay:
            tasks.append(
                self._fetch_pixabay(
                    search_query,
                    input_data.media_types,
                    per_source_limit,
                    input_data.safe_search,
                )
            )
            sources.append("pixabay")

        # Execute all fetches in parallel
        if tasks:
            fetch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, items_or_error in enumerate(fetch_results):
                if isinstance(items_or_error, Exception):
                    result.errors.append(str(items_or_error))
                    self.logger.warning("fetch_error", error=str(items_or_error))
                else:
                    result.items.extend(items_or_error)

        result.total_found = len(result.items)
        result.sources_queried = sources

        return result

    async def _fetch_pexels(
        self,
        query: str,
        media_types: list[MediaType],
        limit: int,
    ) -> list[MediaItem]:
        """Fetch from Pexels API.

        Args:
            query: Search query
            media_types: Types to fetch
            limit: Maximum results

        Returns:
            List of MediaItem
        """
        try:
            return await self.pexels_client.search(query, media_types, limit)
        except Exception as e:
            self.logger.error("pexels_fetch_failed", query=query, error=str(e))
            raise

    async def _fetch_pixabay(
        self,
        query: str,
        media_types: list[MediaType],
        limit: int,
        safe_search: bool,
    ) -> list[MediaItem]:
        """Fetch from Pixabay API.

        Args:
            query: Search query
            media_types: Types to fetch
            limit: Maximum results
            safe_search: Enable safe search

        Returns:
            List of MediaItem
        """
        try:
            return await self.pixabay_client.search(query, media_types, limit, safe_search)
        except Exception as e:
            self.logger.error("pixabay_fetch_failed", query=query, error=str(e))
            raise

    def _serialize_output(self, output: FetchResult) -> dict[str, Any]:
        """Serialize FetchResult for caching."""
        return {
            "items": [item.model_dump(mode="json") for item in output.items],
            "total_found": output.total_found,
            "sources_queried": output.sources_queried,
            "errors": output.errors,
        }

    def _deserialize_output(self, data: dict[str, Any]) -> FetchResult:
        """Deserialize FetchResult from cache."""
        return FetchResult(
            items=[MediaItem.model_validate(item) for item in data.get("items", [])],
            total_found=data.get("total_found", 0),
            sources_queried=data.get("sources_queried", []),
            errors=data.get("errors", []),
        )
