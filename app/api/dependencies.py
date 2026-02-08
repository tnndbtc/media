"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.session import get_async_session
from app.services.cache import CacheService
from app.services.openai_client import OpenAIClient
from app.services.pexels import PexelsClient
from app.services.pixabay import PixabayClient
from app.services.prompt_service import PromptService, get_prompt_cache


@lru_cache
def get_cache_service() -> CacheService:
    """Get cached CacheService instance."""
    settings = get_settings()
    return CacheService(
        redis_url=settings.redis_url,
        password=settings.redis_password.get_secret_value() if settings.redis_password else None,
        default_ttl=settings.cache_ttl_seconds,
        enabled=settings.cache_enabled,
    )


@lru_cache
def get_openai_client() -> OpenAIClient:
    """Get cached OpenAI client instance."""
    settings = get_settings()
    return OpenAIClient(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.openai_model,
        embedding_model=settings.openai_embedding_model,
        max_tokens=settings.openai_max_tokens,
        temperature=settings.openai_temperature,
    )


@lru_cache
def get_pexels_client() -> PexelsClient:
    """Get cached Pexels client instance."""
    settings = get_settings()
    return PexelsClient(
        api_key=settings.pexels_api_key.get_secret_value(),
        base_url=settings.pexels_base_url,
        timeout=settings.http_timeout_seconds,
        max_retries=settings.http_max_retries,
    )


@lru_cache
def get_pixabay_client() -> PixabayClient:
    """Get cached Pixabay client instance."""
    settings = get_settings()
    return PixabayClient(
        api_key=settings.pixabay_api_key.get_secret_value(),
        base_url=settings.pixabay_base_url,
        timeout=settings.http_timeout_seconds,
        max_retries=settings.http_max_retries,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async for session in get_async_session():
        yield session


async def get_prompt_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PromptService:
    """Get prompt service instance."""
    return PromptService(session=session, cache=get_prompt_cache())


# Type aliases for dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
CacheDep = Annotated[CacheService, Depends(get_cache_service)]
OpenAIDep = Annotated[OpenAIClient, Depends(get_openai_client)]
PexelsDep = Annotated[PexelsClient, Depends(get_pexels_client)]
PixabayDep = Annotated[PixabayClient, Depends(get_pixabay_client)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
PromptServiceDep = Annotated[PromptService, Depends(get_prompt_service)]
