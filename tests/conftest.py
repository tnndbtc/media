"""Pytest fixtures for testing."""

import os

# Set dummy API keys before any app imports so that Settings() validation
# succeeds during pytest collection (app/db/session.py calls get_settings()
# at module level, which requires all required fields to be present).
os.environ.setdefault("PEXELS_API_KEY", "test-pexels-key")
os.environ.setdefault("PIXABAY_API_KEY", "test-pixabay-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-openai-key")

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.config.settings import Settings
from app.models.media import MediaDimensions, MediaItem, MediaSource, MediaType, MediaUrls
from app.models.query import GeneratedQuery, LanguageInfo
from app.services.cache import CacheService
from app.services.openai_client import OpenAIClient
from app.services.pexels import PexelsClient
from app.services.pixabay import PixabayClient


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        openai_api_key="test-openai-key",
        pexels_api_key="test-pexels-key",
        pixabay_api_key="test-pixabay-key",
        redis_url="redis://localhost:6379/0",
        cache_enabled=False,
        debug=True,
    )


@pytest.fixture
def mock_cache():
    """Create mock cache service."""
    cache = MagicMock(spec=CacheService)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.get_json = AsyncMock(return_value=None)
    cache.set_json = AsyncMock()
    cache.ping = AsyncMock(return_value=True)
    cache.enabled = False
    return cache


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client."""
    client = MagicMock(spec=OpenAIClient)
    client.is_configured = True
    client.complete = AsyncMock(return_value="test response")
    client.complete_json = AsyncMock(
        return_value={
            "english_query": "sunset ocean",
            "native_query": None,
            "semantic_concepts": ["sunset", "ocean"],
            "keywords": ["sunset", "ocean", "sea"],
            "synonyms": ["sundown", "seascape"],
            "visual_elements": ["orange sky", "water"],
            "mood": "peaceful",
            "style": "natural",
        }
    )
    client.embed = AsyncMock(return_value=[0.1] * 1536)
    client.embed_batch = AsyncMock(return_value=[[0.1] * 1536, [0.2] * 1536])
    return client


@pytest.fixture
def mock_pexels_client():
    """Create mock Pexels client."""
    client = MagicMock(spec=PexelsClient)
    client.health_check = AsyncMock(return_value=True)
    client.search = AsyncMock(return_value=[sample_media_item("pexels")])
    client.search_photos = AsyncMock(return_value={"photos": []})
    client.search_videos = AsyncMock(return_value={"videos": []})
    return client


@pytest.fixture
def mock_pixabay_client():
    """Create mock Pixabay client."""
    client = MagicMock(spec=PixabayClient)
    client.health_check = AsyncMock(return_value=True)
    client.search = AsyncMock(return_value=[sample_media_item("pixabay")])
    client.search_images = AsyncMock(return_value={"hits": []})
    client.search_videos = AsyncMock(return_value={"hits": []})
    return client


@pytest.fixture
def sample_language_info():
    """Create sample language info."""
    return LanguageInfo(
        code="en",
        name="English",
        confidence=0.98,
        is_english=True,
    )


@pytest.fixture
def sample_language_info_chinese():
    """Create sample Chinese language info."""
    return LanguageInfo(
        code="zh-cn",
        name="Chinese (Simplified)",
        confidence=0.95,
        is_english=False,
    )


@pytest.fixture
def sample_generated_query(sample_language_info):
    """Create sample generated query."""
    return GeneratedQuery(
        original_text="sunset over the ocean",
        english_query="sunset ocean",
        native_query=None,
        semantic_concepts=["sunset", "ocean", "nature"],
        keywords=["sunset", "ocean", "sea"],
        synonyms=["sundown", "seascape"],
        visual_elements=["orange sky", "water reflection"],
        mood="peaceful",
        style="natural photography",
        language_info=sample_language_info,
    )


def sample_media_item(source: str = "pexels") -> MediaItem:
    """Create sample media item."""
    return MediaItem(
        id=f"{source}_12345",
        source=MediaSource.PEXELS if source == "pexels" else MediaSource.PIXABAY,
        media_type=MediaType.IMAGE,
        urls=MediaUrls(
            original="https://example.com/original.jpg",
            large="https://example.com/large.jpg",
            medium="https://example.com/medium.jpg",
            small="https://example.com/small.jpg",
            thumbnail="https://example.com/thumb.jpg",
        ),
        dimensions=MediaDimensions(width=1920, height=1080),
        title="Beautiful sunset",
        tags=["sunset", "ocean", "nature"],
        photographer="Test User",
        source_url="https://example.com/photo/12345",
        views=1000,
        downloads=50,
        likes=100,
    )


@pytest.fixture
def sample_media_items():
    """Create list of sample media items."""
    return [
        sample_media_item("pexels"),
        sample_media_item("pixabay"),
    ]
