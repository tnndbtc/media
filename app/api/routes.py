"""API route definitions."""

import logging as std_logging

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app import __version__
from app.api.dependencies import (
    CacheDep,
    OpenAIDep,
    PexelsDep,
    PixabayDep,
    PromptServiceDep,
    SettingsDep,
)
from app.models.requests import AgentRequest, AnalyzeRequest, BatchSearchRequest, SearchRequest
from app.models.responses import (
    AgentKeywords,
    AgentResponse,
    AnalyzeResponse,
    BatchSearchResponse,
    HealthResponse,
    SearchResponse,
)
from app.models.media import MediaType
from app.pipelines.analyze import AnalyzePipeline
from app.pipelines.batch import BatchPipeline
from app.pipelines.search import SearchPipeline
router = APIRouter()


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root to web UI."""
    return RedirectResponse(url="/static/index.html")


def get_search_pipeline(
    settings: SettingsDep,
    cache: CacheDep,
    openai: OpenAIDep,
    pexels: PexelsDep,
    pixabay: PixabayDep,
    prompt_service: PromptServiceDep,
) -> SearchPipeline:
    """Build search pipeline with dependencies."""
    return SearchPipeline(
        settings=settings,
        cache=cache,
        openai_client=openai,
        pexels_client=pexels,
        pixabay_client=pixabay,
        prompt_service=prompt_service,
    )


def get_batch_pipeline(
    settings: SettingsDep,
    cache: CacheDep,
    openai: OpenAIDep,
    pexels: PexelsDep,
    pixabay: PixabayDep,
    prompt_service: PromptServiceDep,
) -> BatchPipeline:
    """Build batch pipeline with dependencies."""
    search_pipeline = SearchPipeline(
        settings=settings,
        cache=cache,
        openai_client=openai,
        pexels_client=pexels,
        pixabay_client=pixabay,
        prompt_service=prompt_service,
    )
    return BatchPipeline(search_pipeline=search_pipeline, settings=settings)


def get_analyze_pipeline(
    settings: SettingsDep,
    cache: CacheDep,
    openai: OpenAIDep,
) -> AnalyzePipeline:
    """Build analyze pipeline with dependencies."""
    return AnalyzePipeline(
        settings=settings,
        cache=cache,
        openai_client=openai,
    )


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(
    cache: CacheDep,
    openai: OpenAIDep,
    pexels: PexelsDep,
    pixabay: PixabayDep,
) -> HealthResponse:
    """Check system health and service availability."""
    services = {}

    # Check Redis
    try:
        await cache.ping()
        services["redis"] = True
    except Exception:
        services["redis"] = False

    # Check OpenAI (lightweight check)
    services["openai"] = openai.is_configured

    # Check Pexels
    try:
        await pexels.health_check()
        services["pexels"] = True
    except Exception:
        services["pexels"] = False

    # Check Pixabay
    try:
        await pixabay.health_check()
        services["pixabay"] = True
    except Exception:
        services["pixabay"] = False

    # Determine overall status
    all_healthy = all(services.values())
    status = "healthy" if all_healthy else "degraded"

    return HealthResponse(
        status=status,
        version=__version__,
        services=services,
    )


@router.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(
    request: SearchRequest,
    pipeline: SearchPipeline = Depends(get_search_pipeline),
) -> SearchResponse:
    """Search for media using natural language in any language.

    Accepts text in any language, detects the language, generates optimized
    search queries, and returns ranked results from Pexels and Pixabay.
    """
    ctx = structlog.contextvars.get_contextvars()
    request_id = ctx.get("request_id", "unknown")
    std_logging.info(f"search_request - \"{request.text[:50]}\" media_types={request.media_type} [request_id: {request_id}]")
    return await pipeline.execute(request)


@router.post("/batch-search", response_model=BatchSearchResponse, tags=["Search"])
async def batch_search(
    request: BatchSearchRequest,
    pipeline: BatchPipeline = Depends(get_batch_pipeline),
) -> BatchSearchResponse:
    """Execute multiple searches concurrently.

    Processes multiple search requests in parallel and optionally
    deduplicates results across all searches.
    """
    ctx = structlog.contextvars.get_contextvars()
    request_id = ctx.get("request_id", "unknown")
    std_logging.info(f"batch_search_request - {len(request.searches)} searches [request_id: {request_id}]")
    return await pipeline.execute(request)


@router.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze(
    request: AnalyzeRequest,
    pipeline: AnalyzePipeline = Depends(get_analyze_pipeline),
) -> AnalyzeResponse:
    """Analyze text without fetching media.

    Performs language detection, query generation, and semantic analysis
    without actually searching for media. Useful for understanding how
    the system interprets input text.
    """
    ctx = structlog.contextvars.get_contextvars()
    request_id = ctx.get("request_id", "unknown")
    std_logging.info(f"analyze_request - \"{request.text[:50]}\" [request_id: {request_id}]")
    return await pipeline.execute(request)


@router.post("/agent", response_model=AgentResponse, tags=["Agent"])
async def agent_search(
    request: AgentRequest,
    pipeline: SearchPipeline = Depends(get_search_pipeline),
) -> AgentResponse:
    """Agent-based media search for external clients.

    Accepts text in any language, searches for both images and videos,
    and returns results with multilingual keywords and processing time.
    The number parameter is split evenly between images and videos.
    """
    import time
    import asyncio

    start_time = time.perf_counter()

    ctx = structlog.contextvars.get_contextvars()
    request_id = ctx.get("request_id", "unknown")
    std_logging.info(f"agent_request - \"{request.text[:50]}\" number={request.number} [request_id: {request_id}]")

    # Split the number evenly between images and videos
    image_limit = request.number // 2
    video_limit = request.number - image_limit  # Handle odd numbers

    # Create search requests for images and videos
    image_request = SearchRequest(
        text=request.text,
        media_type=[MediaType.IMAGE],
        limit=image_limit,
    )
    video_request = SearchRequest(
        text=request.text,
        media_type=[MediaType.VIDEO],
        limit=video_limit,
    )

    # Execute both searches concurrently
    image_response, video_response = await asyncio.gather(
        pipeline.execute(image_request),
        pipeline.execute(video_request),
    )

    # Extract keywords from the query (use image response as reference)
    query = image_response.query

    # Separate English and native keywords from bilingual_keywords
    english_keywords = query.keywords if query.keywords else []
    bilingual = query.bilingual_keywords if query.bilingual_keywords else []

    # Native keywords are bilingual keywords that are not in English keywords
    native_keywords = [kw for kw in bilingual if kw not in english_keywords]

    keywords = AgentKeywords(
        english=english_keywords,
        native=native_keywords,
        bilingual=bilingual,
    )

    processing_time_ms = (time.perf_counter() - start_time) * 1000

    return AgentResponse(
        success=image_response.success and video_response.success,
        keywords=keywords,
        images=image_response.results,
        videos=video_response.results,
        processing_time_ms=processing_time_ms,
    )
