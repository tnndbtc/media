"""API response models."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.media import MediaItem
from app.models.query import GeneratedQuery


class ApiCall(BaseModel):
    """Record of an API invocation."""

    service: str = Field(..., description="Service name (openai, pexels, pixabay)")
    method: str = Field(..., description="Method called (complete_json, embed_batch, search_photos, etc.)")
    cached: bool = Field(default=False, description="Whether the result was from cache")


class QuerySummary(BaseModel):
    """Summary of query processing."""

    original_text: str = Field(..., description="Original input text")
    detected_language: str = Field(..., description="Detected language name")
    language_code: str = Field(..., description="ISO 639-1 language code")
    english_query: str = Field(..., description="Generated English query")
    native_query: str | None = Field(default=None, description="Query in original language")
    keywords: list[str] = Field(default_factory=list, description="Extracted keywords")
    processing_time_ms: float = Field(..., ge=0, description="Query processing time")


class SearchResponse(BaseModel):
    """Response for media search."""

    success: bool = Field(default=True, description="Whether the search was successful")
    query: QuerySummary = Field(..., description="Query processing summary")
    results: list[MediaItem] = Field(default_factory=list, description="Search results")
    total_found: int = Field(..., ge=0, description="Total results found before filtering")
    total_returned: int = Field(..., ge=0, description="Results returned after filtering")
    sources_queried: list[str] = Field(default_factory=list, description="APIs queried")
    apis_invoked: list[ApiCall] = Field(default_factory=list, description="APIs called during request")
    cached: bool = Field(default=False, description="Whether results were from cache")
    processing_time_ms: float = Field(..., ge=0, description="Total processing time")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "query": {
                    "original_text": "sunset over the ocean",
                    "detected_language": "English",
                    "language_code": "en",
                    "english_query": "sunset over ocean",
                    "keywords": ["sunset", "ocean"],
                    "processing_time_ms": 150.5,
                },
                "results": [],
                "total_found": 100,
                "total_returned": 20,
                "sources_queried": ["pexels", "pixabay"],
                "apis_invoked": [
                    {"service": "openai", "method": "complete_json", "cached": False},
                    {"service": "pexels", "method": "search_photos", "cached": False},
                ],
                "cached": False,
                "processing_time_ms": 850.5,
            }
        }


class BatchSearchResponse(BaseModel):
    """Response for batch media search."""

    success: bool = Field(default=True)
    searches: list[SearchResponse] = Field(default_factory=list)
    total_results: int = Field(..., ge=0)
    duplicates_removed: int = Field(default=0, ge=0)
    processing_time_ms: float = Field(..., ge=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnalyzeResponse(BaseModel):
    """Response for text analysis."""

    success: bool = Field(default=True)
    query: GeneratedQuery = Field(..., description="Full query analysis")
    suggestions: list[str] = Field(
        default_factory=list, description="Suggested search refinements"
    )
    processing_time_ms: float = Field(..., ge=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    services: dict[str, bool] = Field(
        default_factory=dict, description="Individual service health"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "services": {
                    "redis": True,
                    "openai": True,
                    "pexels": True,
                    "pixabay": True,
                },
            }
        }
