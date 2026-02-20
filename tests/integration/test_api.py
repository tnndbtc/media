"""Integration tests for API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import (
    get_cache_service,
    get_openai_client,
    get_pexels_client,
    get_pixabay_client,
    get_prompt_service,
)


@pytest.fixture
def mock_dependencies(mock_cache, mock_openai_client, mock_pexels_client, mock_pixabay_client):
    """Override dependencies with mocks."""

    def override_cache():
        return mock_cache

    def override_openai():
        return mock_openai_client

    def override_pexels():
        return mock_pexels_client

    def override_pixabay():
        return mock_pixabay_client

    def override_prompt_service():
        # Return None so QueryGeneratorAgent falls back to hardcoded prompts,
        # avoiding real aiosqlite DB access inside the test client's event loop.
        return None

    app.dependency_overrides[get_cache_service] = override_cache
    app.dependency_overrides[get_openai_client] = override_openai
    app.dependency_overrides[get_pexels_client] = override_pexels
    app.dependency_overrides[get_pixabay_client] = override_pixabay
    app.dependency_overrides[get_prompt_service] = override_prompt_service

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_dependencies):
    """Create test client with mocked dependencies."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client):
        """Test health check returns status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data


class TestSearchEndpoint:
    """Tests for /search endpoint."""

    def test_search_basic(self, client):
        """Test basic search request."""
        response = client.post(
            "/search",
            json={
                "text": "sunset over the ocean",
                "media_type": ["image"],
                "limit": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "query" in data
        assert "results" in data

    def test_search_with_video(self, client):
        """Test search including video."""
        response = client.post(
            "/search",
            json={
                "text": "mountain landscape",
                "media_type": ["image", "video"],
                "limit": 5,
            },
        )

        assert response.status_code == 200

    def test_search_multilingual(self, client):
        """Test search with non-English text."""
        response = client.post(
            "/search",
            json={
                "text": "这张照片展示了美丽的中国山水风景",
                "media_type": ["image"],
                "limit": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"]["language_code"] in ["zh", "zh-cn", "zh-tw"]

    def test_search_invalid_request(self, client):
        """Test search with invalid request."""
        response = client.post(
            "/search",
            json={
                "text": "",  # Empty text should fail
                "media_type": ["image"],
            },
        )

        assert response.status_code == 422  # Validation error

    def test_search_with_filters(self, client):
        """Test search with quality filter."""
        response = client.post(
            "/search",
            json={
                "text": "beautiful flowers",
                "media_type": ["image"],
                "limit": 10,
                "min_quality_score": 0.5,
                "safe_search": True,
            },
        )

        assert response.status_code == 200


class TestBatchSearchEndpoint:
    """Tests for /batch-search endpoint."""

    def test_batch_search(self, client):
        """Test batch search with multiple queries."""
        response = client.post(
            "/batch-search",
            json={
                "searches": [
                    {"text": "sunset", "media_type": ["image"], "limit": 5},
                    {"text": "mountains", "media_type": ["image"], "limit": 5},
                ],
                "deduplicate_across": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["searches"]) == 2

    def test_batch_search_empty(self, client):
        """Test batch search with empty list."""
        response = client.post(
            "/batch-search",
            json={
                "searches": [],
            },
        )

        assert response.status_code == 422  # Validation error


class TestAnalyzeEndpoint:
    """Tests for /analyze endpoint."""

    def test_analyze_text(self, client):
        """Test text analysis."""
        response = client.post(
            "/analyze",
            json={
                "text": "A beautiful sunset over the calm ocean",
                "include_synonyms": True,
                "include_visual_elements": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "query" in data
        assert "suggestions" in data

    def test_analyze_chinese(self, client):
        """Test analysis of Chinese text."""
        response = client.post(
            "/analyze",
            json={
                "text": "海上美丽的日落",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"]["language_info"]["is_english"] is False
