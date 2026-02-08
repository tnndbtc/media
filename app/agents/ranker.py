"""Semantic ranking agent for media results."""

from dataclasses import dataclass
from typing import Any

from app.agents.base import BaseAgent
from app.models.media import MediaItem
from app.models.query import GeneratedQuery
from app.ranking.deduplication import deduplicate_results
from app.ranking.scorer import MediaScorer
from app.services.cache import CacheService
from app.services.openai_client import OpenAIClient


@dataclass
class RankInput:
    """Input for ranking."""

    items: list[MediaItem]
    query: GeneratedQuery
    limit: int = 20
    min_quality_score: float = 0.0


@dataclass
class RankResult:
    """Result from ranking."""

    items: list[MediaItem]
    duplicates_removed: int = 0


class RankerAgent(BaseAgent[RankInput, RankResult]):
    """Agent for ranking and deduplicating media results.

    Uses semantic scoring, keyword matching, and quality metrics
    to rank results by relevance.
    """

    name = "ranker"
    cache_enabled = False  # Don't cache ranking results

    def __init__(
        self,
        openai_client: OpenAIClient | None = None,
        cache: CacheService | None = None,
        weights: dict[str, float] | None = None,
    ):
        """Initialize ranker.

        Args:
            openai_client: Optional OpenAI client for semantic scoring
            cache: Optional cache service
            weights: Custom ranking weights
        """
        super().__init__(cache)
        self.openai_client = openai_client
        self.scorer = MediaScorer(openai_client=openai_client, weights=weights)

    async def process(self, input_data: RankInput) -> RankResult:
        """Rank and deduplicate media items.

        Args:
            input_data: Ranking input with items and query

        Returns:
            RankResult with ranked items
        """
        if not input_data.items:
            return RankResult(items=[], duplicates_removed=0)

        # Deduplicate first
        unique_items, dups_removed = deduplicate_results(input_data.items)

        # Score all items
        scored_items = await self.scorer.score_items(unique_items, input_data.query)

        # Filter by minimum quality score
        if input_data.min_quality_score > 0:
            scored_items = [
                item
                for item in scored_items
                if item.final_score >= input_data.min_quality_score
            ]

        # Sort by final score descending
        scored_items.sort(key=lambda x: x.final_score, reverse=True)

        # Apply limit
        limited_items = scored_items[: input_data.limit]

        return RankResult(
            items=limited_items,
            duplicates_removed=dups_removed,
        )

    def _serialize_output(self, output: RankResult) -> dict[str, Any]:
        """Serialize RankResult."""
        return {
            "items": [item.model_dump(mode="json") for item in output.items],
            "duplicates_removed": output.duplicates_removed,
        }

    def _deserialize_output(self, data: dict[str, Any]) -> RankResult:
        """Deserialize RankResult."""
        return RankResult(
            items=[MediaItem.model_validate(item) for item in data.get("items", [])],
            duplicates_removed=data.get("duplicates_removed", 0),
        )
