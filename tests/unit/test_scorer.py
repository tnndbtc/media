"""Tests for media scoring."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.media import MediaDimensions, MediaItem, MediaSource, MediaType, MediaUrls
from app.models.query import GeneratedQuery, LanguageInfo
from app.ranking.scorer import MediaScorer


def create_media_item(
    id_str: str = "1",
    width: int = 1920,
    height: int = 1080,
    views: int = 1000,
    tags: list[str] | None = None,
) -> MediaItem:
    """Create a test media item."""
    return MediaItem(
        id=f"test_{id_str}",
        source=MediaSource.PEXELS,
        media_type=MediaType.IMAGE,
        urls=MediaUrls(
            original="https://example.com/original.jpg",
        ),
        dimensions=MediaDimensions(width=width, height=height),
        source_url="https://example.com/photo/1",
        tags=tags or [],
        views=views,
        downloads=50,
        likes=100,
    )


def create_query() -> GeneratedQuery:
    """Create a test query."""
    return GeneratedQuery(
        original_text="sunset over ocean",
        english_query="sunset ocean",
        native_query=None,
        semantic_concepts=["sunset", "ocean"],
        keywords=["sunset", "ocean", "sea"],
        synonyms=["sundown"],
        visual_elements=["orange sky"],
        mood="peaceful",
        style="natural",
        language_info=LanguageInfo(
            code="en",
            name="English",
            confidence=0.98,
            is_english=True,
        ),
    )


class TestMediaScorer:
    """Tests for MediaScorer."""

    @pytest.fixture
    def scorer(self):
        """Create scorer without OpenAI client."""
        return MediaScorer()

    @pytest.fixture
    def scorer_with_openai(self):
        """Create scorer with mock OpenAI client."""
        mock_client = MagicMock()
        mock_client.embed_batch = AsyncMock(
            return_value=[
                [0.1] * 1536,  # Query embedding
                [0.2] * 1536,  # Item 1 embedding
            ]
        )
        return MediaScorer(openai_client=mock_client)

    @pytest.mark.asyncio
    async def test_score_empty_items(self, scorer):
        """Test scoring empty list."""
        result = await scorer.score_items([], create_query())
        assert result == []

    @pytest.mark.asyncio
    async def test_score_single_item(self, scorer):
        """Test scoring a single item."""
        items = [create_media_item()]
        query = create_query()

        result = await scorer.score_items(items, query)

        assert len(result) == 1
        assert 0.0 <= result[0].final_score <= 1.0
        assert 0.0 <= result[0].quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_quality_score_high_resolution(self, scorer):
        """Test that high resolution gets high quality score."""
        items = [create_media_item(width=3840, height=2160)]  # 4K
        query = create_query()

        result = await scorer.score_items(items, query)

        assert result[0].quality_score >= 0.85

    @pytest.mark.asyncio
    async def test_quality_score_low_resolution(self, scorer):
        """Test that low resolution gets lower quality score."""
        items = [create_media_item(width=640, height=480)]
        query = create_query()

        result = await scorer.score_items(items, query)

        assert result[0].quality_score < 0.7

    @pytest.mark.asyncio
    async def test_keyword_matching(self, scorer):
        """Test keyword matching affects score."""
        item_with_tags = create_media_item(tags=["sunset", "ocean", "beach"])
        item_without_tags = create_media_item(tags=["mountain", "snow"])
        query = create_query()

        result = await scorer.score_items([item_with_tags, item_without_tags], query)

        # Item with matching tags should score higher
        assert result[0].final_score > result[1].final_score

    @pytest.mark.asyncio
    async def test_popularity_scoring(self, scorer):
        """Test popularity affects score."""
        popular_item = create_media_item(id_str="1", views=100000)
        unpopular_item = create_media_item(id_str="2", views=10)
        query = create_query()

        result = await scorer.score_items([popular_item, unpopular_item], query)

        # Popular item should have higher score
        popular_score = result[0].final_score
        unpopular_score = result[1].final_score

        # They should differ (popularity is 10% weight)
        assert popular_score != unpopular_score

    @pytest.mark.asyncio
    async def test_custom_weights(self):
        """Test custom weight configuration."""
        custom_weights = {
            "semantic_relevance": 0.0,
            "keyword_match": 0.0,
            "visual_quality": 1.0,  # Only quality matters
            "popularity": 0.0,
            "recency": 0.0,
            "source_diversity": 0.0,
        }
        scorer = MediaScorer(weights=custom_weights)

        high_quality = create_media_item(id_str="1", width=3840, height=2160)
        low_quality = create_media_item(id_str="2", width=640, height=480)

        result = await scorer.score_items([high_quality, low_quality], create_query())

        # With only quality weight, high res should score much higher
        assert result[0].final_score > result[1].final_score

    def test_cosine_similarity(self, scorer):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        # Identical vectors should have similarity 1.0
        sim = scorer._cosine_similarity(vec1, vec2)
        assert sim == 1.0

        # Orthogonal vectors should have similarity 0.5 (normalized from 0)
        vec3 = [0.0, 1.0, 0.0]
        sim = scorer._cosine_similarity(vec1, vec3)
        assert sim == 0.5

    def test_cosine_similarity_empty(self, scorer):
        """Test cosine similarity with mismatched vectors."""
        sim = scorer._cosine_similarity([1, 2], [1, 2, 3])
        assert sim == 0.0

        sim = scorer._cosine_similarity([], [])
        assert sim == 0.0
