"""Tests for agent classes."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.language_detector import LanguageDetectorAgent
from app.agents.query_generator import QueryGeneratorAgent, QueryInput
from app.agents.media_fetcher import FetchInput, MediaFetcherAgent
from app.agents.ranker import RankInput, RankerAgent
from app.models.media import MediaType
from app.models.query import LanguageInfo


class TestLanguageDetectorAgent:
    """Tests for LanguageDetectorAgent."""

    @pytest.fixture
    def agent(self, mock_cache, mock_openai_client):
        """Create agent instance."""
        return LanguageDetectorAgent(
            cache=mock_cache,
            openai_client=mock_openai_client,
        )

    @pytest.mark.asyncio
    async def test_detect_english(self, agent):
        """Test detecting English text."""
        result = await agent.process("This is a beautiful sunset")

        assert result.code == "en"
        assert result.is_english is True
        assert result.confidence > 0.8

    @pytest.mark.asyncio
    async def test_detect_chinese(self, agent):
        """Test detecting Chinese text."""
        result = await agent.process("海上美丽的日落")

        assert result.is_english is False
        assert "Chinese" in result.name or "zh" in result.code


class TestQueryGeneratorAgent:
    """Tests for QueryGeneratorAgent."""

    @pytest.fixture
    def agent(self, mock_cache, mock_openai_client):
        """Create agent instance."""
        return QueryGeneratorAgent(
            openai_client=mock_openai_client,
            cache=mock_cache,
        )

    @pytest.mark.asyncio
    async def test_generate_query(self, agent, sample_language_info):
        """Test query generation."""
        input_data = QueryInput(
            text="sunset over the ocean",
            language_info=sample_language_info,
        )

        result = await agent.process(input_data)

        assert result.original_text == "sunset over the ocean"
        assert result.english_query is not None
        assert len(result.keywords) > 0

    @pytest.mark.asyncio
    async def test_generate_query_with_fallback(self, mock_cache, sample_language_info):
        """Test fallback when OpenAI fails."""
        mock_client = MagicMock()
        mock_client.complete_json = AsyncMock(side_effect=Exception("API Error"))

        agent = QueryGeneratorAgent(
            openai_client=mock_client,
            cache=mock_cache,
        )

        input_data = QueryInput(
            text="sunset over the ocean",
            language_info=sample_language_info,
        )

        # Should not raise, should use fallback
        result = await agent.process(input_data)

        assert result.original_text == "sunset over the ocean"


class TestMediaFetcherAgent:
    """Tests for MediaFetcherAgent."""

    @pytest.fixture
    def agent(self, mock_cache, mock_pexels_client, mock_pixabay_client):
        """Create agent instance."""
        return MediaFetcherAgent(
            pexels_client=mock_pexels_client,
            pixabay_client=mock_pixabay_client,
            cache=mock_cache,
        )

    @pytest.mark.asyncio
    async def test_fetch_media(self, agent, sample_generated_query):
        """Test media fetching."""
        input_data = FetchInput(
            query=sample_generated_query,
            media_types=[MediaType.IMAGE],
            limit=10,
        )

        result = await agent.process(input_data)

        assert result.total_found >= 0
        assert "pexels" in result.sources_queried or "pixabay" in result.sources_queried

    @pytest.mark.asyncio
    async def test_fetch_with_source_filter(self, agent, sample_generated_query):
        """Test fetching with source filter."""
        input_data = FetchInput(
            query=sample_generated_query,
            media_types=[MediaType.IMAGE],
            limit=10,
            include_sources=["pexels"],
        )

        result = await agent.process(input_data)

        assert "pexels" in result.sources_queried
        # Pixabay should not be queried
        assert "pixabay" not in result.sources_queried


class TestRankerAgent:
    """Tests for RankerAgent."""

    @pytest.fixture
    def agent(self, mock_cache, mock_openai_client):
        """Create agent instance."""
        return RankerAgent(
            openai_client=mock_openai_client,
            cache=mock_cache,
        )

    @pytest.mark.asyncio
    async def test_rank_empty_items(self, agent, sample_generated_query):
        """Test ranking empty list."""
        input_data = RankInput(
            items=[],
            query=sample_generated_query,
            limit=10,
        )

        result = await agent.process(input_data)

        assert result.items == []
        assert result.duplicates_removed == 0

    @pytest.mark.asyncio
    async def test_rank_items(self, agent, sample_generated_query, sample_media_items):
        """Test ranking items."""
        input_data = RankInput(
            items=sample_media_items,
            query=sample_generated_query,
            limit=10,
        )

        result = await agent.process(input_data)

        assert len(result.items) <= 10
        # Items should be sorted by score
        if len(result.items) > 1:
            assert result.items[0].final_score >= result.items[-1].final_score

    @pytest.mark.asyncio
    async def test_rank_with_quality_filter(self, agent, sample_generated_query, sample_media_items):
        """Test ranking with quality filter."""
        input_data = RankInput(
            items=sample_media_items,
            query=sample_generated_query,
            limit=10,
            min_quality_score=0.9,  # Very high threshold
        )

        result = await agent.process(input_data)

        # All returned items should meet quality threshold
        for item in result.items:
            assert item.final_score >= 0.9 or len(result.items) == 0
