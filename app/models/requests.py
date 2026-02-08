"""API request models."""

from pydantic import BaseModel, Field

from app.models.media import MediaType


class SearchRequest(BaseModel):
    """Request for media search."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language text to search for (any language)",
    )
    media_type: list[MediaType] = Field(
        default=[MediaType.IMAGE],
        min_length=1,
        description="Types of media to search for",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )
    min_quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum quality score filter",
    )
    include_sources: list[str] | None = Field(
        default=None,
        description="Filter to specific sources (pexels, pixabay). None means all.",
    )
    safe_search: bool = Field(
        default=True,
        description="Enable safe search filtering",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "text": "sunset over the ocean",
                "media_type": ["image"],
                "limit": 20,
                "min_quality_score": 0.5,
                "safe_search": True,
            }
        }


class BatchSearchRequest(BaseModel):
    """Request for batch media search."""

    searches: list[SearchRequest] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of search requests to process concurrently",
    )
    deduplicate_across: bool = Field(
        default=True,
        description="Remove duplicate results across all searches",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "searches": [
                    {"text": "sunset over the ocean", "media_type": ["image"], "limit": 10},
                    {"text": "mountain landscape", "media_type": ["image"], "limit": 10},
                ],
                "deduplicate_across": True,
            }
        }


class AnalyzeRequest(BaseModel):
    """Request for text analysis without media search."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language text to analyze (any language)",
    )
    include_synonyms: bool = Field(
        default=True,
        description="Include synonym suggestions",
    )
    include_visual_elements: bool = Field(
        default=True,
        description="Include visual element suggestions",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "text": "海上美丽的日落",
                "include_synonyms": True,
                "include_visual_elements": True,
            }
        }
