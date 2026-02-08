"""Multilingual processing utilities."""

from app.multilingual.detector import detect_language
from app.multilingual.prompts import (
    QUERY_GENERATION_PROMPT,
    QUERY_GENERATION_SYSTEM,
    SEMANTIC_ANALYSIS_PROMPT,
)

__all__ = [
    "detect_language",
    "QUERY_GENERATION_PROMPT",
    "QUERY_GENERATION_SYSTEM",
    "SEMANTIC_ANALYSIS_PROMPT",
]
