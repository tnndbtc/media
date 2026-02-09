"""Main search pipeline orchestrator."""

import logging as std_logging
import time

import structlog

from app.agents.language_detector import LanguageDetectorAgent
from app.agents.media_fetcher import FetchInput, MediaFetcherAgent
from app.agents.query_generator import QueryGeneratorAgent, QueryInput
from app.agents.ranker import RankInput, RankerAgent
from app.config.settings import Settings
from app.models.requests import SearchRequest
from app.models.responses import ApiCall, QuerySummary, SearchResponse
from app.services.cache import CacheService
from app.services.openai_client import OpenAIClient
from app.services.pexels import PexelsClient
from app.services.pixabay import PixabayClient
from app.services.prompt_service import PromptService
from app.utils.hashing import generate_cache_key


class SearchPipeline:
    """Main orchestration pipeline for media search.

    Coordinates the following steps:
    1. Language detection
    2. Query generation (via OpenAI)
    3. Media fetching (Pexels + Pixabay)
    4. Semantic ranking
    5. Result caching
    """

    def __init__(
        self,
        settings: Settings,
        cache: CacheService,
        openai_client: OpenAIClient,
        pexels_client: PexelsClient,
        pixabay_client: PixabayClient,
        prompt_service: PromptService | None = None,
    ):
        """Initialize the search pipeline.

        Args:
            settings: Application settings
            cache: Cache service
            openai_client: OpenAI client
            pexels_client: Pexels API client
            pixabay_client: Pixabay API client
            prompt_service: Optional prompt service for dynamic prompts
        """
        self.settings = settings
        self.cache = cache
        self.openai_client = openai_client
        self.pexels_client = pexels_client
        self.pixabay_client = pixabay_client
        self.prompt_service = prompt_service

        # Initialize agents
        self.language_detector = LanguageDetectorAgent(
            cache=cache,
            openai_client=openai_client,
        )
        self.query_generator = QueryGeneratorAgent(
            openai_client=openai_client,
            cache=cache,
            prompt_service=prompt_service,
        )
        self.media_fetcher = MediaFetcherAgent(
            pexels_client=pexels_client,
            pixabay_client=pixabay_client,
            cache=cache,
        )
        self.ranker = RankerAgent(
            openai_client=openai_client,
            cache=cache,
            weights={
                "semantic_relevance": settings.weight_semantic_relevance,
                "keyword_match": settings.weight_keyword_match,
                "visual_quality": settings.weight_visual_quality,
                "popularity": settings.weight_popularity,
                "recency": settings.weight_recency,
                "source_diversity": settings.weight_source_diversity,
            },
        )

    async def execute(self, request: SearchRequest) -> SearchResponse:
        """Execute the search pipeline.

        Args:
            request: Search request

        Returns:
            Search response with results
        """
        start_time = time.perf_counter()

        # Check cache for full response
        cache_key = self._get_cache_key(request)
        cached_response = await self._get_cached_response(cache_key)
        if cached_response:
            cached_response.cached = True
            cached_response.processing_time_ms = (time.perf_counter() - start_time) * 1000
            return cached_response

        # Track API calls
        apis_invoked: list[ApiCall] = []

        # Step 1: Detect language
        query_start = time.perf_counter()
        language_info = await self.language_detector.execute(request.text)
        apis_invoked.append(
            ApiCall(
                service="openai",
                method="complete_json",
                cached=self.language_detector._last_cache_hit,
            )
        )
        ctx = structlog.contextvars.get_contextvars()
        request_id = ctx.get("request_id", "unknown")
        std_logging.info(f"language_detected - {language_info.code} confidence={language_info.confidence} [request_id: {request_id}]")

        # Step 2: Generate optimized query
        query_input = QueryInput(text=request.text, language_info=language_info)
        generated_query = await self.query_generator.execute(query_input)
        apis_invoked.append(
            ApiCall(
                service="openai",
                method="complete_json",
                cached=self.query_generator._last_cache_hit,
            )
        )
        query_time_ms = (time.perf_counter() - query_start) * 1000

        std_logging.info(f"query_generated - \"{generated_query.english_query}\" keywords={generated_query.bilingual_keywords} [request_id: {request_id}]")

        # Step 3: Fetch media from APIs
        fetch_input = FetchInput(
            query=generated_query,
            media_types=request.media_type,
            limit=request.limit * 2,  # Fetch extra for ranking
            include_sources=request.include_sources,
            safe_search=request.safe_search,
        )
        fetch_result = await self.media_fetcher.execute(fetch_input)
        media_cached = self.media_fetcher._last_cache_hit

        # Add API calls for each source queried
        if "pexels" in fetch_result.sources_queried:
            apis_invoked.append(
                ApiCall(service="pexels", method="search_photos", cached=media_cached)
            )
        if "pixabay" in fetch_result.sources_queried:
            apis_invoked.append(
                ApiCall(service="pixabay", method="search_images", cached=media_cached)
            )

        std_logging.info(f"media_fetched - {fetch_result.total_found} items from {fetch_result.sources_queried} [request_id: {request_id}]")

        # Step 4: Rank and deduplicate
        rank_input = RankInput(
            items=fetch_result.items,
            query=generated_query,
            limit=request.limit,
            min_quality_score=request.min_quality_score,
        )
        rank_result = await self.ranker.execute(rank_input)

        # Ranker uses embeddings if items were scored
        if rank_result.items:
            apis_invoked.append(
                ApiCall(service="openai", method="embed_batch", cached=False)
            )

        std_logging.info(f"results_ranked - {len(rank_result.items)} returned, {rank_result.duplicates_removed} duplicates removed [request_id: {request_id}]")

        # Build response
        processing_time_ms = (time.perf_counter() - start_time) * 1000

        response = SearchResponse(
            success=True,
            query=QuerySummary(
                original_text=request.text,
                detected_language=language_info.name,
                language_code=language_info.code,
                english_query=generated_query.english_query,
                native_query=generated_query.native_query,
                keywords=generated_query.keywords,
                processing_time_ms=query_time_ms,
            ),
            results=rank_result.items,
            total_found=fetch_result.total_found,
            total_returned=len(rank_result.items),
            sources_queried=fetch_result.sources_queried,
            apis_invoked=apis_invoked,
            cached=False,
            processing_time_ms=processing_time_ms,
        )

        # Cache the response
        await self._cache_response(cache_key, response)

        return response

    def _get_cache_key(self, request: SearchRequest) -> str:
        """Generate cache key for a search request."""
        return generate_cache_key(
            "search",
            request.text,
            [mt.value for mt in request.media_type],
            request.limit,
            request.min_quality_score,
            request.include_sources,
            request.safe_search,
        )

    async def _get_cached_response(self, key: str) -> SearchResponse | None:
        """Get cached search response."""
        try:
            data = await self.cache.get_json(key)
            if data:
                return SearchResponse.model_validate(data)
        except Exception as e:
            std_logging.warning(f"cache_get_failed - error={str(e)}")
        return None

    async def _cache_response(self, key: str, response: SearchResponse) -> None:
        """Cache search response."""
        try:
            await self.cache.set_json(
                key,
                response.model_dump(mode="json"),
                ttl=self.settings.cache_ttl_seconds,
            )
        except Exception as e:
            std_logging.warning(f"cache_set_failed - error={str(e)}")
