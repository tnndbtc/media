"""Batch search pipeline for concurrent processing."""

import asyncio
import time

from app.config.settings import Settings
from app.models.requests import BatchSearchRequest
from app.models.responses import BatchSearchResponse
from app.pipelines.search import SearchPipeline
from app.ranking.deduplication import deduplicate_across_batches
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BatchPipeline:
    """Pipeline for processing multiple search requests concurrently.

    Executes searches in parallel and optionally deduplicates
    results across all searches.
    """

    def __init__(
        self,
        search_pipeline: SearchPipeline,
        settings: Settings,
    ):
        """Initialize batch pipeline.

        Args:
            search_pipeline: Search pipeline instance for individual searches
            settings: Application settings
        """
        self.search_pipeline = search_pipeline
        self.settings = settings

    async def execute(self, request: BatchSearchRequest) -> BatchSearchResponse:
        """Execute batch search.

        Args:
            request: Batch search request

        Returns:
            Batch search response
        """
        start_time = time.perf_counter()

        # Validate batch size
        if len(request.searches) > self.settings.max_batch_size:
            request.searches = request.searches[: self.settings.max_batch_size]
            logger.warning(
                "batch_truncated",
                max_size=self.settings.max_batch_size,
            )

        # Execute all searches in parallel
        tasks = [self.search_pipeline.execute(search) for search in request.searches]
        search_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_results = []
        for i, result in enumerate(search_results):
            if isinstance(result, Exception):
                logger.error(
                    "batch_search_failed",
                    index=i,
                    error=str(result),
                )
            else:
                successful_results.append(result)

        # Deduplicate across results if requested
        duplicates_removed = 0
        if request.deduplicate_across and len(successful_results) > 1:
            # Extract result items from each search
            batch_items = [r.results for r in successful_results]
            deduplicated_batches, duplicates_removed = deduplicate_across_batches(batch_items)

            # Update results with deduplicated items
            for i, items in enumerate(deduplicated_batches):
                successful_results[i].results = items
                successful_results[i].total_returned = len(items)

        # Calculate totals
        total_results = sum(len(r.results) for r in successful_results)
        processing_time_ms = (time.perf_counter() - start_time) * 1000

        return BatchSearchResponse(
            success=True,
            searches=successful_results,
            total_results=total_results,
            duplicates_removed=duplicates_removed,
            processing_time_ms=processing_time_ms,
        )
