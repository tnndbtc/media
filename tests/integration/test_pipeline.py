"""Integration tests for search pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.media import MediaType
from app.models.requests import AnalyzeRequest, BatchSearchRequest, SearchRequest
from app.pipelines.analyze import AnalyzePipeline
from app.pipelines.batch import BatchPipeline
from app.pipelines.search import SearchPipeline


class TestSearchPipeline:
    """Tests for SearchPipeline."""

    @pytest.fixture
    def pipeline(
        self,
        mock_settings,
        mock_cache,
        mock_openai_client,
        mock_pexels_client,
        mock_pixabay_client,
    ):
        """Create pipeline instance."""
        return SearchPipeline(
            settings=mock_settings,
            cache=mock_cache,
            openai_client=mock_openai_client,
            pexels_client=mock_pexels_client,
            pixabay_client=mock_pixabay_client,
        )

    @pytest.mark.asyncio
    async def test_execute_search(self, pipeline):
        """Test full search pipeline execution."""
        request = SearchRequest(
            text="sunset over the ocean",
            media_type=[MediaType.IMAGE],
            limit=10,
        )

        response = await pipeline.execute(request)

        assert response.success is True
        assert response.query.original_text == "sunset over the ocean"
        assert response.query.detected_language is not None
        assert response.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_execute_multilingual_search(self, pipeline):
        """Test search with non-English text."""
        request = SearchRequest(
            text="这张照片展示了美丽的中国山水风景",
            media_type=[MediaType.IMAGE],
            limit=5,
        )

        response = await pipeline.execute(request)

        assert response.success is True
        assert response.query.language_code in ["zh", "zh-cn", "zh-tw"]

    @pytest.mark.asyncio
    async def test_execute_with_video(self, pipeline):
        """Test search including video type."""
        request = SearchRequest(
            text="nature scenery",
            media_type=[MediaType.IMAGE, MediaType.VIDEO],
            limit=10,
        )

        response = await pipeline.execute(request)

        assert response.success is True


class TestBatchPipeline:
    """Tests for BatchPipeline."""

    @pytest.fixture
    def search_pipeline(
        self,
        mock_settings,
        mock_cache,
        mock_openai_client,
        mock_pexels_client,
        mock_pixabay_client,
    ):
        """Create search pipeline instance."""
        return SearchPipeline(
            settings=mock_settings,
            cache=mock_cache,
            openai_client=mock_openai_client,
            pexels_client=mock_pexels_client,
            pixabay_client=mock_pixabay_client,
        )

    @pytest.fixture
    def pipeline(self, search_pipeline, mock_settings):
        """Create batch pipeline instance."""
        return BatchPipeline(
            search_pipeline=search_pipeline,
            settings=mock_settings,
        )

    @pytest.mark.asyncio
    async def test_execute_batch(self, pipeline):
        """Test batch search execution."""
        request = BatchSearchRequest(
            searches=[
                SearchRequest(text="sunset", media_type=[MediaType.IMAGE], limit=5),
                SearchRequest(text="mountains", media_type=[MediaType.IMAGE], limit=5),
            ],
            deduplicate_across=True,
        )

        response = await pipeline.execute(request)

        assert response.success is True
        assert len(response.searches) == 2
        assert response.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_execute_batch_without_dedup(self, pipeline):
        """Test batch search without deduplication."""
        request = BatchSearchRequest(
            searches=[
                SearchRequest(text="ocean", media_type=[MediaType.IMAGE], limit=5),
            ],
            deduplicate_across=False,
        )

        response = await pipeline.execute(request)

        assert response.success is True
        assert response.duplicates_removed == 0


class TestAnalyzePipeline:
    """Tests for AnalyzePipeline."""

    @pytest.fixture
    def pipeline(self, mock_settings, mock_cache, mock_openai_client):
        """Create analyze pipeline instance."""
        return AnalyzePipeline(
            settings=mock_settings,
            cache=mock_cache,
            openai_client=mock_openai_client,
        )

    @pytest.mark.asyncio
    async def test_execute_analyze(self, pipeline):
        """Test text analysis execution."""
        request = AnalyzeRequest(
            text="A beautiful sunset over the calm ocean",
            include_synonyms=True,
            include_visual_elements=True,
        )

        response = await pipeline.execute(request)

        assert response.success is True
        assert response.query.original_text == request.text
        assert response.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_execute_analyze_chinese(self, pipeline):
        """Test analysis of Chinese text."""
        request = AnalyzeRequest(
            text="海上美丽的日落",
        )

        response = await pipeline.execute(request)

        assert response.success is True
        assert response.query.language_info.is_english is False
