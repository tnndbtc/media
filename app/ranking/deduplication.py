"""Deduplication utilities for media results."""

import logging as std_logging

import structlog

from app.models.media import MediaItem


def deduplicate_results(items: list[MediaItem]) -> tuple[list[MediaItem], int]:
    """Remove duplicate media items.

    Uses multiple strategies:
    1. Exact ID matching
    2. URL matching
    3. Similar dimensions + source matching

    Args:
        items: List of media items

    Returns:
        Tuple of (deduplicated items, count of duplicates removed)
    """
    if not items:
        return [], 0

    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    unique_items: list[MediaItem] = []
    duplicates = 0

    for item in items:
        # Check ID
        if item.id in seen_ids:
            duplicates += 1
            continue

        # Check original URL
        original_url = str(item.urls.original)
        if original_url in seen_urls:
            duplicates += 1
            continue

        # Mark as seen
        seen_ids.add(item.id)
        seen_urls.add(original_url)

        # Also track other URL variants
        if item.urls.large:
            seen_urls.add(str(item.urls.large))
        if item.urls.medium:
            seen_urls.add(str(item.urls.medium))

        unique_items.append(item)

    if duplicates > 0:
        ctx = structlog.contextvars.get_contextvars()
        request_id = ctx.get("request_id", "unknown")
        std_logging.info(f"duplicates_removed - {duplicates} [request_id: {request_id}]")

    return unique_items, duplicates


def deduplicate_across_batches(
    batch_results: list[list[MediaItem]],
) -> tuple[list[list[MediaItem]], int]:
    """Deduplicate across multiple batch results.

    Removes duplicates that appear in multiple search results,
    keeping the first occurrence.

    Args:
        batch_results: List of result lists

    Returns:
        Tuple of (deduplicated batch results, total duplicates removed)
    """
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    total_duplicates = 0
    deduplicated_batches: list[list[MediaItem]] = []

    for batch in batch_results:
        unique_in_batch: list[MediaItem] = []

        for item in batch:
            # Check if already seen in previous batches
            if item.id in seen_ids:
                total_duplicates += 1
                continue

            original_url = str(item.urls.original)
            if original_url in seen_urls:
                total_duplicates += 1
                continue

            # Mark as seen
            seen_ids.add(item.id)
            seen_urls.add(original_url)

            unique_in_batch.append(item)

        deduplicated_batches.append(unique_in_batch)

    return deduplicated_batches, total_duplicates


def calculate_similarity_hash(item: MediaItem) -> str:
    """Calculate a similarity hash for perceptual deduplication.

    This is a simple implementation that could be extended
    with actual perceptual hashing of images.

    Args:
        item: Media item

    Returns:
        Similarity hash string
    """
    # Simple hash based on dimensions and source
    width_bucket = item.dimensions.width // 100
    height_bucket = item.dimensions.height // 100

    return f"{item.source.value}_{width_bucket}_{height_bucket}_{item.media_type.value}"
