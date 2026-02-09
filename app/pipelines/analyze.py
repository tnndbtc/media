"""Text analysis pipeline without media fetching."""

import logging as std_logging
import time

import structlog

from app.agents.language_detector import LanguageDetectorAgent
from app.agents.query_generator import QueryGeneratorAgent, QueryInput
from app.config.settings import Settings
from app.models.requests import AnalyzeRequest
from app.models.responses import AnalyzeResponse
from app.services.cache import CacheService
from app.services.openai_client import OpenAIClient
from app.utils.hashing import generate_cache_key


class AnalyzePipeline:
    """Pipeline for text analysis without media fetching.

    Useful for understanding how the system interprets input text
    before actually searching for media.
    """

    def __init__(
        self,
        settings: Settings,
        cache: CacheService,
        openai_client: OpenAIClient,
    ):
        """Initialize analyze pipeline.

        Args:
            settings: Application settings
            cache: Cache service
            openai_client: OpenAI client
        """
        self.settings = settings
        self.cache = cache
        self.openai_client = openai_client

        # Initialize agents
        self.language_detector = LanguageDetectorAgent(
            cache=cache,
            openai_client=openai_client,
        )
        self.query_generator = QueryGeneratorAgent(
            openai_client=openai_client,
            cache=cache,
        )

    async def execute(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """Execute text analysis.

        Args:
            request: Analysis request

        Returns:
            Analysis response
        """
        start_time = time.perf_counter()

        # Check cache
        cache_key = self._get_cache_key(request)
        cached = await self._get_cached(cache_key)
        if cached:
            cached.processing_time_ms = (time.perf_counter() - start_time) * 1000
            return cached

        # Detect language
        language_info = await self.language_detector.execute(request.text)
        ctx = structlog.contextvars.get_contextvars()
        request_id = ctx.get("request_id", "unknown")
        std_logging.info(f"language_detected - {language_info.code} confidence={language_info.confidence} [request_id: {request_id}]")

        # Generate query analysis
        query_input = QueryInput(text=request.text, language_info=language_info)
        generated_query = await self.query_generator.execute(query_input)

        # Generate search suggestions
        suggestions = self._generate_suggestions(generated_query, request)

        processing_time_ms = (time.perf_counter() - start_time) * 1000

        response = AnalyzeResponse(
            success=True,
            query=generated_query,
            suggestions=suggestions,
            processing_time_ms=processing_time_ms,
        )

        # Cache response
        await self._cache_response(cache_key, response)

        return response

    def _generate_suggestions(self, query, request: AnalyzeRequest) -> list[str]:
        """Generate search refinement suggestions.

        Args:
            query: Generated query
            request: Original request

        Returns:
            List of suggestions
        """
        suggestions = []

        # Suggest using synonyms
        if request.include_synonyms and query.synonyms:
            for syn in query.synonyms[:3]:
                suggestions.append(f"Try searching for: {syn}")

        # Suggest visual elements
        if request.include_visual_elements and query.visual_elements:
            elements = ", ".join(query.visual_elements[:3])
            suggestions.append(f"Include visual elements: {elements}")

        # Suggest mood-based refinement
        if query.mood:
            suggestions.append(f"Refine by mood: {query.mood}")

        # Suggest style-based refinement
        if query.style:
            suggestions.append(f"Try style: {query.style}")

        return suggestions

    def _get_cache_key(self, request: AnalyzeRequest) -> str:
        """Generate cache key for analysis request."""
        return generate_cache_key(
            "analyze",
            request.text,
            request.include_synonyms,
            request.include_visual_elements,
        )

    async def _get_cached(self, key: str) -> AnalyzeResponse | None:
        """Get cached analysis response."""
        try:
            data = await self.cache.get_json(key)
            if data:
                return AnalyzeResponse.model_validate(data)
        except Exception as e:
            std_logging.warning(f"cache_get_failed - error={str(e)}")
        return None

    async def _cache_response(self, key: str, response: AnalyzeResponse) -> None:
        """Cache analysis response."""
        try:
            await self.cache.set_json(
                key,
                response.model_dump(mode="json"),
                ttl=self.settings.cache_ttl_seconds,
            )
        except Exception as e:
            std_logging.warning(f"cache_set_failed - error={str(e)}")
