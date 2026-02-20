"""Tests for deduplication utilities."""

import pytest

from app.models.media import MediaDimensions, MediaItem, MediaSource, MediaType, MediaUrls
from app.ranking.deduplication import deduplicate_across_batches, deduplicate_results


def create_media_item(
    id_suffix: str,
    source: MediaSource = MediaSource.PEXELS,
    url_suffix: str = "",
) -> MediaItem:
    """Create a test media item."""
    return MediaItem(
        id=f"{source.value}_{id_suffix}",
        source=source,
        media_type=MediaType.IMAGE,
        urls=MediaUrls(
            original=f"https://example.com/{source.value}/{id_suffix}{url_suffix}.jpg",
            large=f"https://example.com/{source.value}/{id_suffix}_large.jpg",
        ),
        dimensions=MediaDimensions(width=1920, height=1080),
        source_url=f"https://example.com/photo/{id_suffix}",
    )


class TestDeduplication:
    """Tests for deduplication functions."""

    def test_deduplicate_empty_list(self):
        """Test deduplication of empty list."""
        result, count = deduplicate_results([])

        assert result == []
        assert count == 0

    def test_deduplicate_no_duplicates(self):
        """Test deduplication when there are no duplicates."""
        items = [
            create_media_item("1"),
            create_media_item("2"),
            create_media_item("3"),
        ]

        result, count = deduplicate_results(items)

        assert len(result) == 3
        assert count == 0

    def test_deduplicate_by_id(self):
        """Test deduplication by matching ID."""
        items = [
            create_media_item("1"),
            create_media_item("1"),  # Duplicate ID
            create_media_item("2"),
        ]

        result, count = deduplicate_results(items)

        assert len(result) == 2
        assert count == 1
        assert all(item.id in ["pexels_1", "pexels_2"] for item in result)

    def test_deduplicate_by_url(self):
        """Test deduplication by matching URL."""
        items = [
            create_media_item("1"),
            create_media_item("2", url_suffix=""),  # Same URL as item 1 if id was 1
            create_media_item("1", source=MediaSource.PIXABAY, url_suffix="_alt"),
        ]

        result, count = deduplicate_results(items)

        # All should be unique since URLs are different
        assert len(result) == 3
        assert count == 0

    def test_deduplicate_preserves_order(self):
        """Test that deduplication preserves original order."""
        items = [
            create_media_item("3"),
            create_media_item("1"),
            create_media_item("3"),  # Duplicate
            create_media_item("2"),
        ]

        result, count = deduplicate_results(items)

        assert len(result) == 3
        assert result[0].id == "pexels_3"
        assert result[1].id == "pexels_1"
        assert result[2].id == "pexels_2"

    def test_deduplicate_across_batches_empty(self):
        """Test cross-batch deduplication with empty input."""
        result, count = deduplicate_across_batches([])

        assert result == []
        assert count == 0

    def test_deduplicate_across_batches(self):
        """Test cross-batch deduplication."""
        batch1 = [create_media_item("1"), create_media_item("2")]
        batch2 = [create_media_item("2"), create_media_item("3")]  # "2" is duplicate
        batch3 = [create_media_item("1"), create_media_item("4")]  # "1" is duplicate

        result, count = deduplicate_across_batches([batch1, batch2, batch3])

        assert len(result) == 3
        assert len(result[0]) == 2  # batch1 unchanged
        assert len(result[1]) == 1  # batch2 has "2" removed
        assert len(result[2]) == 1  # batch3 has "1" removed
        assert count == 2

    def test_deduplicate_mixed_sources(self):
        """Test deduplication with different sources."""
        items = [
            create_media_item("1", source=MediaSource.PEXELS),
            create_media_item("1", source=MediaSource.PIXABAY),  # Different source, same suffix
        ]

        result, count = deduplicate_results(items)

        # Should keep both since IDs are different (include source prefix)
        assert len(result) == 2
        assert count == 0
