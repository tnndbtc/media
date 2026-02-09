"""Multilingual processing utilities."""

from app.multilingual.detector import detect_language
from app.multilingual.prompts import (
    QUERY_GENERATION_SYSTEM,
    QUERY_GENERATION_USER_TEMPLATE,
    QUERY_GENERATION_PROMPT,  # Deprecated alias
)

__all__ = [
    "detect_language",
    "QUERY_GENERATION_SYSTEM",
    "QUERY_GENERATION_USER_TEMPLATE",
    "QUERY_GENERATION_PROMPT",
]
