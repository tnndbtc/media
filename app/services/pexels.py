"""Pexels API client."""

from typing import Any

from app.models.media import (
    MediaDimensions,
    MediaItem,
    MediaSource,
    MediaType,
    MediaUrls,
)
from app.services.base_client import BaseHTTPClient
from app.utils.hashing import generate_media_id
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ALLOWED_PEXELS_DOMAINS = {"images.pexels.com", "videos.pexels.com", "www.pexels.com"}
ALLOWED_PEXELS_DOMAINS = {"images.pexels.com", "videos.pexels.com"}


def _is_valid_pexels_url(url: str | None) -> bool:
    """Check if URL is from Pexels CDN."""
    if not url:
        return True  # None/empty is OK (optional fields)
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        return any(host.endswith(domain) for domain in ALLOWED_PEXELS_DOMAINS)
    except Exception:
        return False


class PexelsClient(BaseHTTPClient):
    """Client for Pexels API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.pexels.com/v1",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize Pexels client.

        Args:
            api_key: Pexels API key
            base_url: API base URL
            timeout: Request timeout
            max_retries: Maximum retries
        """
        super().__init__(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            service_name="pexels",
        )
        self.api_key = api_key

    def _get_headers(self) -> dict[str, str]:
        """Get headers with API key."""
        headers = super()._get_headers()
        headers["Authorization"] = self.api_key
        return headers

    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            await self.search_photos("test", per_page=1)
            return True
        except Exception:
            return False

    async def search_photos(
        self,
        query: str,
        per_page: int = 20,
        page: int = 1,
        orientation: str | None = None,
        size: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        """Search for photos.

        Args:
            query: Search query
            per_page: Results per page (max 80)
            page: Page number
            orientation: Filter by orientation (landscape, portrait, square)
            size: Filter by size (large, medium, small)
            color: Filter by color

        Returns:
            Raw API response
        """
        params: dict[str, Any] = {
            "query": query,
            "per_page": min(per_page, 80),
            "page": page,
        }

        if orientation:
            params["orientation"] = orientation
        if size:
            params["size"] = size
        if color:
            params["color"] = color

        return await self.get("search", params=params)

    async def search_videos(
        self,
        query: str,
        per_page: int = 20,
        page: int = 1,
        orientation: str | None = None,
        size: str | None = None,
    ) -> dict[str, Any]:
        """Search for videos.

        Args:
            query: Search query
            per_page: Results per page (max 80)
            page: Page number
            orientation: Filter by orientation
            size: Filter by size

        Returns:
            Raw API response
        """
        params: dict[str, Any] = {
            "query": query,
            "per_page": min(per_page, 80),
            "page": page,
        }

        if orientation:
            params["orientation"] = orientation
        if size:
            params["size"] = size

        # Videos API uses different base URL
        self.base_url = "https://api.pexels.com/videos"
        try:
            return await self.get("search", params=params)
        finally:
            self.base_url = "https://api.pexels.com/v1"

    async def search(
        self,
        query: str,
        media_types: list[MediaType],
        limit: int = 20,
    ) -> list[MediaItem]:
        """Search for media and return unified MediaItem list.

        Args:
            query: Search query
            media_types: Types of media to search
            limit: Maximum results

        Returns:
            List of MediaItem objects
        """
        results: list[MediaItem] = []

        # Calculate per-type limit
        per_type_limit = limit // len(media_types) if media_types else limit

        for media_type in media_types:
            try:
                if media_type == MediaType.IMAGE:
                    response = await self.search_photos(query, per_page=per_type_limit)
                    items = self._parse_photos(response.get("photos", []))
                else:
                    response = await self.search_videos(query, per_page=per_type_limit)
                    items = self._parse_videos(response.get("videos", []))

                results.extend(items)
            except Exception as e:
                logger.warning(
                    "pexels_search_failed",
                    query=query,
                    media_type=media_type,
                    error=str(e),
                )

        return results[:limit]

    def _parse_photos(self, photos: list[dict[str, Any]]) -> list[MediaItem]:
        """Parse Pexels photo response into MediaItem list."""
        items = []
        for photo in photos:
            try:
                src = photo.get("src", {})
                original_url = src.get("original", src.get("large2x", ""))
                if not _is_valid_pexels_url(original_url):
                    logger.debug("pexels_photo_external_url_filtered", url=original_url)
                    continue
                items.append(
                    MediaItem(
                        id=generate_media_id("pexels", photo["id"]),
                        source=MediaSource.PEXELS,
                        media_type=MediaType.IMAGE,
                        urls=MediaUrls(
                            original=src.get("original", src.get("large2x", "")),
                            large=src.get("large"),
                            medium=src.get("medium"),
                            small=src.get("small"),
                            thumbnail=src.get("tiny"),
                        ),
                        dimensions=MediaDimensions(
                            width=photo.get("width", 0),
                            height=photo.get("height", 0),
                        ),
                        title=photo.get("alt"),
                        photographer=photo.get("photographer"),
                        photographer_url=photo.get("photographer_url"),
                        source_url=photo.get("url", ""),
                        likes=photo.get("liked", 0) or 0,
                        raw_data=photo,
                    )
                )
            except Exception as e:
                logger.warning("pexels_photo_parse_failed", error=str(e))

        return items

    def _parse_videos(self, videos: list[dict[str, Any]]) -> list[MediaItem]:
        """Parse Pexels video response into MediaItem list."""
        items = []
        for video in videos:
            try:
                video_files = video.get("video_files", [])
                video_pictures = video.get("video_pictures", [])

                # Get best quality video file
                best_file = max(
                    video_files,
                    key=lambda f: (f.get("width", 0) or 0) * (f.get("height", 0) or 0),
                    default={},
                )

                # Get thumbnail
                thumbnail = video_pictures[0].get("picture") if video_pictures else None

                video_url = best_file.get("link", "")
                if not _is_valid_pexels_url(video_url):
                    logger.debug("pexels_video_external_url_filtered", url=video_url)
                    continue

                items.append(
                    MediaItem(
                        id=generate_media_id("pexels", video["id"]),
                        source=MediaSource.PEXELS,
                        media_type=MediaType.VIDEO,
                        urls=MediaUrls(
                            original=best_file.get("link", ""),
                            thumbnail=thumbnail,
                        ),
                        dimensions=MediaDimensions(
                            width=video.get("width", 0),
                            height=video.get("height", 0),
                        ),
                        title=None,
                        photographer=video.get("user", {}).get("name"),
                        photographer_url=video.get("user", {}).get("url"),
                        source_url=video.get("url", ""),
                        duration=video.get("duration"),
                        raw_data=video,
                    )
                )
            except Exception as e:
                logger.warning("pexels_video_parse_failed", error=str(e))

        return items
