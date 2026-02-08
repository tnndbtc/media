"""Media item models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class MediaType(str, Enum):
    """Type of media content."""

    IMAGE = "image"
    VIDEO = "video"


class MediaSource(str, Enum):
    """Source API for the media."""

    PEXELS = "pexels"
    PIXABAY = "pixabay"


class MediaDimensions(BaseModel):
    """Media dimensions."""

    width: int = Field(ge=0)
    height: int = Field(ge=0)

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio."""
        if self.height == 0:
            return 0.0
        return self.width / self.height


class MediaUrls(BaseModel):
    """URLs for different sizes of the media."""

    original: HttpUrl
    large: HttpUrl | None = None
    medium: HttpUrl | None = None
    small: HttpUrl | None = None
    thumbnail: HttpUrl | None = None


class MediaItem(BaseModel):
    """Unified media item from any source."""

    id: str = Field(..., description="Unique identifier")
    source: MediaSource = Field(..., description="Source API")
    media_type: MediaType = Field(..., description="Type of media")
    urls: MediaUrls = Field(..., description="Media URLs at different sizes")
    dimensions: MediaDimensions = Field(..., description="Media dimensions")

    title: str | None = Field(default=None, description="Media title")
    description: str | None = Field(default=None, description="Media description")
    tags: list[str] = Field(default_factory=list, description="Associated tags")

    photographer: str | None = Field(default=None, description="Creator name")
    photographer_url: HttpUrl | None = Field(default=None, description="Creator profile URL")

    views: int = Field(default=0, ge=0, description="View count")
    downloads: int = Field(default=0, ge=0, description="Download count")
    likes: int = Field(default=0, ge=0, description="Like count")

    duration: float | None = Field(default=None, ge=0, description="Video duration in seconds")
    created_at: datetime | None = Field(default=None, description="Creation date")

    source_url: HttpUrl = Field(..., description="URL to original source page")

    # Scoring fields (populated during ranking)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    final_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Raw data for debugging
    raw_data: dict[str, Any] | None = Field(default=None, exclude=True)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "pexels_12345",
                "source": "pexels",
                "media_type": "image",
                "urls": {
                    "original": "https://images.pexels.com/photos/12345/original.jpg",
                    "large": "https://images.pexels.com/photos/12345/large.jpg",
                    "medium": "https://images.pexels.com/photos/12345/medium.jpg",
                },
                "dimensions": {"width": 1920, "height": 1080},
                "title": "Sunset over ocean",
                "tags": ["sunset", "ocean", "nature"],
                "photographer": "John Doe",
                "views": 15000,
                "downloads": 500,
                "source_url": "https://www.pexels.com/photo/12345/",
                "relevance_score": 0.95,
                "final_score": 0.87,
            }
        }
