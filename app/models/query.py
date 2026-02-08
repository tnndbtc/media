"""Query and language detection models."""

from pydantic import BaseModel, Field


class LanguageInfo(BaseModel):
    """Detected language information."""

    code: str = Field(..., description="ISO 639-1 language code (e.g., 'en', 'zh', 'es')")
    name: str = Field(..., description="Language name in English")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    is_english: bool = Field(..., description="Whether the detected language is English")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "code": "zh",
                "name": "Chinese",
                "confidence": 0.98,
                "is_english": False,
            }
        }


class GeneratedQuery(BaseModel):
    """Generated search query with semantic understanding."""

    original_text: str = Field(..., description="Original input text")
    english_query: str = Field(..., description="Optimized English search query")
    native_query: str | None = Field(
        default=None, description="Query in the original language (if not English)"
    )

    semantic_concepts: list[str] = Field(
        default_factory=list, description="Extracted semantic concepts"
    )
    keywords: list[str] = Field(default_factory=list, description="Key search terms")
    bilingual_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords in both English and original language for search"
    )
    synonyms: list[str] = Field(default_factory=list, description="Related synonyms")

    visual_elements: list[str] = Field(
        default_factory=list, description="Visual elements to search for"
    )
    mood: str | None = Field(default=None, description="Mood/atmosphere of the query")
    style: str | None = Field(default=None, description="Visual style preference")

    language_info: LanguageInfo = Field(..., description="Detected language information")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "original_text": "海上美丽的日落",
                "english_query": "beautiful sunset over ocean",
                "native_query": "海上日落 美丽 自然",
                "semantic_concepts": ["sunset", "ocean", "beauty", "nature"],
                "keywords": ["sunset", "ocean", "sea", "dusk"],
                "bilingual_keywords": ["sunset", "日落", "ocean", "海洋", "beautiful", "美丽"],
                "synonyms": ["sundown", "twilight", "seascape"],
                "visual_elements": ["orange sky", "water reflection", "horizon"],
                "mood": "peaceful",
                "style": "natural photography",
                "language_info": {
                    "code": "zh",
                    "name": "Chinese",
                    "confidence": 0.98,
                    "is_english": False,
                },
            }
        }


class QueryVariant(BaseModel):
    """A variant of the search query for API calls."""

    query: str = Field(..., description="The search query string")
    language: str = Field(default="en", description="Language of the query")
    priority: int = Field(default=1, ge=1, le=10, description="Search priority")
