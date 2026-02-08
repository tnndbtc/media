"""Media scoring algorithm for ranking results."""

import asyncio
import math
from datetime import datetime, timezone

from app.models.media import MediaItem, MediaSource
from app.models.query import GeneratedQuery
from app.services.openai_client import OpenAIClient
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Default ranking weights
DEFAULT_WEIGHTS = {
    "semantic_relevance": 0.35,
    "keyword_match": 0.20,
    "visual_quality": 0.15,
    "popularity": 0.10,
    "recency": 0.10,
    "source_diversity": 0.10,
}


class MediaScorer:
    """Scorer for ranking media results by relevance and quality."""

    def __init__(
        self,
        openai_client: OpenAIClient | None = None,
        weights: dict[str, float] | None = None,
    ):
        """Initialize scorer.

        Args:
            openai_client: Optional OpenAI client for semantic scoring
            weights: Custom weights for ranking factors
        """
        self.openai_client = openai_client
        self.weights = weights or DEFAULT_WEIGHTS.copy()

        # Normalize weights
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    async def score_items(
        self,
        items: list[MediaItem],
        query: GeneratedQuery,
    ) -> list[MediaItem]:
        """Score all items based on query relevance.

        Args:
            items: Items to score
            query: Generated query for relevance calculation

        Returns:
            Items with updated scores
        """
        if not items:
            return []

        # Calculate semantic embeddings if OpenAI is available
        query_embedding = None
        item_embeddings = None

        if self.openai_client:
            try:
                query_embedding, item_embeddings = await self._get_embeddings(items, query)
            except Exception as e:
                logger.warning("embedding_generation_failed", error=str(e))

        # Track source distribution for diversity scoring
        source_counts = self._count_sources(items)

        # Score each item
        scored_items = []
        for i, item in enumerate(items):
            item_embedding = item_embeddings[i] if item_embeddings else None
            scored_item = self._score_item(
                item=item,
                query=query,
                query_embedding=query_embedding,
                item_embedding=item_embedding,
                source_counts=source_counts,
            )
            scored_items.append(scored_item)

        return scored_items

    async def _get_embeddings(
        self,
        items: list[MediaItem],
        query: GeneratedQuery,
    ) -> tuple[list[float], list[list[float]]]:
        """Get embeddings for query and items.

        Args:
            items: Items to embed
            query: Query to embed

        Returns:
            Tuple of (query_embedding, item_embeddings)
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not configured")

        # Prepare texts for embedding
        query_text = f"{query.english_query} {' '.join(query.keywords)}"
        item_texts = [self._get_item_text(item) for item in items]

        # Batch embed all texts
        all_texts = [query_text] + item_texts
        embeddings = await self.openai_client.embed_batch(all_texts)

        query_embedding = embeddings[0]
        item_embeddings = embeddings[1:]

        return query_embedding, item_embeddings

    def _get_item_text(self, item: MediaItem) -> str:
        """Get searchable text from item for embedding.

        Args:
            item: Media item

        Returns:
            Text representation
        """
        parts = []

        if item.title:
            parts.append(item.title)
        if item.description:
            parts.append(item.description)
        if item.tags:
            parts.append(" ".join(item.tags))

        return " ".join(parts) if parts else "media"

    def _score_item(
        self,
        item: MediaItem,
        query: GeneratedQuery,
        query_embedding: list[float] | None,
        item_embedding: list[float] | None,
        source_counts: dict[MediaSource, int],
    ) -> MediaItem:
        """Calculate scores for a single item.

        Args:
            item: Item to score
            query: Search query
            query_embedding: Query embedding vector
            item_embedding: Item embedding vector
            source_counts: Distribution of sources

        Returns:
            Item with updated scores
        """
        scores = {}

        # Semantic relevance (embedding similarity)
        if query_embedding and item_embedding:
            scores["semantic_relevance"] = self._cosine_similarity(query_embedding, item_embedding)
        else:
            scores["semantic_relevance"] = 0.5  # Default middle score

        # Keyword match
        scores["keyword_match"] = self._calculate_keyword_score(item, query)

        # Visual quality
        scores["visual_quality"] = self._calculate_quality_score(item)

        # Popularity
        scores["popularity"] = self._calculate_popularity_score(item)

        # Recency
        scores["recency"] = self._calculate_recency_score(item)

        # Source diversity (favor underrepresented sources)
        scores["source_diversity"] = self._calculate_diversity_score(item, source_counts)

        # Calculate weighted final score
        final_score = sum(
            scores.get(factor, 0) * weight for factor, weight in self.weights.items()
        )

        # Update item with scores
        item.relevance_score = scores["semantic_relevance"]
        item.quality_score = scores["visual_quality"]
        item.final_score = min(1.0, max(0.0, final_score))

        return item

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0-1)
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Normalize to 0-1 range (cosine similarity is -1 to 1)
        return (similarity + 1) / 2

    def _calculate_keyword_score(self, item: MediaItem, query: GeneratedQuery) -> float:
        """Calculate keyword match score.

        Args:
            item: Media item
            query: Generated query

        Returns:
            Score 0-1
        """
        # Combine all query keywords
        query_terms = set(
            term.lower()
            for term in query.keywords + query.semantic_concepts + query.synonyms
        )

        if not query_terms:
            return 0.5

        # Get item terms
        item_terms = set()
        if item.title:
            item_terms.update(item.title.lower().split())
        if item.description:
            item_terms.update(item.description.lower().split())
        if item.tags:
            item_terms.update(tag.lower() for tag in item.tags)

        if not item_terms:
            return 0.0

        # Calculate overlap
        matches = len(query_terms & item_terms)
        score = matches / len(query_terms)

        return min(1.0, score)

    def _calculate_quality_score(self, item: MediaItem) -> float:
        """Calculate visual quality score based on resolution.

        Args:
            item: Media item

        Returns:
            Score 0-1
        """
        width = item.dimensions.width
        height = item.dimensions.height
        pixels = width * height

        # Score based on resolution tiers
        if pixels >= 4000000:  # 4K+ (e.g., 2560x1440 or higher)
            return 1.0
        elif pixels >= 2000000:  # 1080p+
            return 0.85
        elif pixels >= 1000000:  # 720p+
            return 0.7
        elif pixels >= 500000:
            return 0.5
        else:
            return 0.3

    def _calculate_popularity_score(self, item: MediaItem) -> float:
        """Calculate popularity score based on views/downloads.

        Args:
            item: Media item

        Returns:
            Score 0-1
        """
        # Use log scale for popularity metrics
        views = item.views or 0
        downloads = item.downloads or 0
        likes = item.likes or 0

        # Weighted combination
        popularity = views * 0.5 + downloads * 1.5 + likes * 2.0

        if popularity <= 0:
            return 0.3

        # Logarithmic scaling with reasonable thresholds
        log_pop = math.log10(popularity + 1)
        score = min(1.0, log_pop / 5.0)  # 100k interactions = 1.0

        return score

    def _calculate_recency_score(self, item: MediaItem) -> float:
        """Calculate recency score based on creation date.

        Args:
            item: Media item

        Returns:
            Score 0-1
        """
        if not item.created_at:
            return 0.5  # Unknown date

        now = datetime.now(timezone.utc)
        age_days = (now - item.created_at).days

        # Decay function: recent content scores higher
        if age_days <= 30:
            return 1.0
        elif age_days <= 180:
            return 0.8
        elif age_days <= 365:
            return 0.6
        elif age_days <= 730:
            return 0.4
        else:
            return 0.2

    def _count_sources(self, items: list[MediaItem]) -> dict[MediaSource, int]:
        """Count items per source.

        Args:
            items: List of items

        Returns:
            Source count dictionary
        """
        counts: dict[MediaSource, int] = {}
        for item in items:
            counts[item.source] = counts.get(item.source, 0) + 1
        return counts

    def _calculate_diversity_score(
        self,
        item: MediaItem,
        source_counts: dict[MediaSource, int],
    ) -> float:
        """Calculate source diversity score.

        Favors items from underrepresented sources to ensure balance.

        Args:
            item: Media item
            source_counts: Distribution of sources

        Returns:
            Score 0-1
        """
        total = sum(source_counts.values())
        if total == 0:
            return 0.5

        item_source_count = source_counts.get(item.source, 0)
        source_ratio = item_source_count / total

        # Inverse ratio: favor less common sources
        diversity_score = 1.0 - source_ratio

        return diversity_score
