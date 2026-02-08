"""Ranking and deduplication module."""

from app.ranking.deduplication import deduplicate_results
from app.ranking.scorer import MediaScorer

__all__ = ["MediaScorer", "deduplicate_results"]
