"""Pixabay API client."""

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

# ALLOWED_PIXABAY_DOMAINS = {"pixabay.com", "cdn.pixabay.com", "i.vimeocdn.com"}
ALLOWED_PIXABAY_DOMAINS = {"pixabay.com", "cdn.pixabay.com"}
BLOCKED_DOMAINS = {"istockphoto.com", "istock.com", "shutterstock.com", "gettyimages.com", "adobe.com"}


def _is_valid_pixabay_url(url: str | None) -> bool:
    """Check if URL is from Pixabay CDN and not an external paid source."""
    if not url:
        return True  # None/empty is OK (optional fields)
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        # Block known paid stock sites
        if any(blocked in host for blocked in BLOCKED_DOMAINS):
            return False
        # Allow Pixabay domains
        return any(host.endswith(domain) for domain in ALLOWED_PIXABAY_DOMAINS)
    except Exception:
        return False


class PixabayClient(BaseHTTPClient):
    """Client for Pixabay API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://pixabay.com/api",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize Pixabay client.

        Args:
            api_key: Pixabay API key
            base_url: API base URL
            timeout: Request timeout
            max_retries: Maximum retries
        """
        super().__init__(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            service_name="pixabay",
        )
        self.api_key = api_key

    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            await self.search_images("test", per_page=3)
            return True
        except Exception:
            return False

    async def search_images(
        self,
        query: str,
        per_page: int = 20,
        page: int = 1,
        image_type: str = "all",
        orientation: str = "all",
        category: str | None = None,
        min_width: int = 0,
        min_height: int = 0,
        colors: str | None = None,
        safesearch: bool = True,
        order: str = "popular",
    ) -> dict[str, Any]:
        """Search for images.

        Args:
            query: Search query
            per_page: Results per page (3-200)
            page: Page number
            image_type: Type (all, photo, illustration, vector)
            orientation: Orientation (all, horizontal, vertical)
            category: Category filter
            min_width: Minimum width
            min_height: Minimum height
            colors: Color filter
            safesearch: Enable safe search
            order: Order by (popular, latest)

        Returns:
            Raw API response
        """
        params: dict[str, Any] = {
            "key": self.api_key,
            "q": query,
            "per_page": min(max(per_page, 3), 200),
            "page": page,
            "image_type": image_type,
            "orientation": orientation,
            "safesearch": str(safesearch).lower(),
            "order": order,
        }

        if category:
            params["category"] = category
        if min_width > 0:
            params["min_width"] = min_width
        if min_height > 0:
            params["min_height"] = min_height
        if colors:
            params["colors"] = colors

        return await self.get("/", params=params)

    async def search_videos(
        self,
        query: str,
        per_page: int = 20,
        page: int = 1,
        video_type: str = "all",
        category: str | None = None,
        min_width: int = 0,
        min_height: int = 0,
        safesearch: bool = True,
        order: str = "popular",
    ) -> dict[str, Any]:
        """Search for videos.

        Args:
            query: Search query
            per_page: Results per page (3-200)
            page: Page number
            video_type: Type (all, film, animation)
            category: Category filter
            min_width: Minimum width
            min_height: Minimum height
            safesearch: Enable safe search
            order: Order by (popular, latest)

        Returns:
            Raw API response
        """
        params: dict[str, Any] = {
            "key": self.api_key,
            "q": query,
            "per_page": min(max(per_page, 3), 200),
            "page": page,
            "video_type": video_type,
            "safesearch": str(safesearch).lower(),
            "order": order,
        }

        if category:
            params["category"] = category
        if min_width > 0:
            params["min_width"] = min_width
        if min_height > 0:
            params["min_height"] = min_height

        return await self.get("/videos/", params=params)

    async def search(
        self,
        query: str,
        media_types: list[MediaType],
        limit: int = 20,
        safesearch: bool = True,
    ) -> list[MediaItem]:
        """Search for media and return unified MediaItem list.

        Args:
            query: Search query
            media_types: Types of media to search
            limit: Maximum results
            safesearch: Enable safe search

        Returns:
            List of MediaItem objects
        """
        results: list[MediaItem] = []

        # Calculate per-type limit
        per_type_limit = limit // len(media_types) if media_types else limit

        for media_type in media_types:
            try:
                if media_type == MediaType.IMAGE:
                    response = await self.search_images(
                        query, per_page=per_type_limit, safesearch=safesearch
                    )
                    items = self._parse_images(response.get("hits", []))
                else:
                    response = await self.search_videos(
                        query, per_page=per_type_limit, safesearch=safesearch
                    )
                    items = self._parse_videos(response.get("hits", []))

                results.extend(items)
            except Exception as e:
                logger.warning(
                    "pixabay_search_failed",
                    query=query,
                    media_type=media_type,
                    error=str(e),
                )

        return results[:limit]

    def _parse_images(self, images: list[dict[str, Any]]) -> list[MediaItem]:
        """Parse Pixabay image response into MediaItem list."""
        items = []
        for image in images:
            try:
                # Parse tags
                tags = [t.strip() for t in image.get("tags", "").split(",") if t.strip()]

                original_url = image.get("largeImageURL", image.get("webformatURL", ""))
                if not _is_valid_pixabay_url(original_url):
                    logger.debug("pixabay_image_external_url_filtered", url=original_url)
                    continue

                items.append(
                    MediaItem(
                        id=generate_media_id("pixabay", image["id"]),
                        source=MediaSource.PIXABAY,
                        media_type=MediaType.IMAGE,
                        urls=MediaUrls(
                            original=image.get("largeImageURL", image.get("webformatURL", "")),
                            large=image.get("largeImageURL"),
                            medium=image.get("webformatURL"),
                            small=image.get("previewURL"),
                            thumbnail=image.get("previewURL"),
                        ),
                        dimensions=MediaDimensions(
                            width=image.get("imageWidth", 0),
                            height=image.get("imageHeight", 0),
                        ),
                        tags=tags,
                        photographer=image.get("user"),
                        photographer_url=f"https://pixabay.com/users/{image.get('user_id', '')}/",
                        source_url=image.get("pageURL", ""),
                        views=image.get("views", 0),
                        downloads=image.get("downloads", 0),
                        likes=image.get("likes", 0),
                        raw_data=image,
                    )
                )
            except Exception as e:
                logger.warning("pixabay_image_parse_failed", error=str(e))

        return items

    def _parse_videos(self, videos: list[dict[str, Any]]) -> list[MediaItem]:
        """Parse Pixabay video response into MediaItem list."""
        items = []
        for video in videos:
            try:
                # Parse tags
                tags = [t.strip() for t in video.get("tags", "").split(",") if t.strip()]

                # Get video files
                video_files = video.get("videos", {})

                # Get best quality
                best_quality = None
                for quality in ["large", "medium", "small", "tiny"]:
                    if quality in video_files and video_files[quality].get("url"):
                        best_quality = video_files[quality]
                        break

                if not best_quality:
                    continue

                # Get dimensions from best quality video
                width = best_quality.get("width", 0)
                height = best_quality.get("height", 0)

                video_url = best_quality.get("url", "")
                if not _is_valid_pixabay_url(video_url):
                    logger.debug("pixabay_video_external_url_filtered", url=video_url)
                    continue

                items.append(
                    MediaItem(
                        id=generate_media_id("pixabay", video["id"]),
                        source=MediaSource.PIXABAY,
                        media_type=MediaType.VIDEO,
                        urls=MediaUrls(
                            original=best_quality.get("url", ""),
                            large=video_files.get("large", {}).get("url"),
                            medium=video_files.get("medium", {}).get("url"),
                            small=video_files.get("small", {}).get("url"),
                            thumbnail=video.get("picture_id"),
                        ),
                        dimensions=MediaDimensions(
                            width=width,
                            height=height,
                        ),
                        tags=tags,
                        photographer=video.get("user"),
                        photographer_url=f"https://pixabay.com/users/{video.get('user_id', '')}/",
                        source_url=video.get("pageURL", ""),
                        views=video.get("views", 0),
                        downloads=video.get("downloads", 0),
                        likes=video.get("likes", 0),
                        duration=video.get("duration"),
                        raw_data=video,
                    )
                )
            except Exception as e:
                logger.warning("pixabay_video_parse_failed", error=str(e))

        return items
