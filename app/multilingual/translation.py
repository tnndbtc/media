"""Translation helpers for multilingual support."""

from app.services.openai_client import OpenAIClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def translate_to_english(
    text: str,
    source_language: str,
    openai_client: OpenAIClient,
) -> str:
    """Translate text to English for search purposes.

    Args:
        text: Text to translate
        source_language: Source language name
        openai_client: OpenAI client instance

    Returns:
        English translation
    """
    if source_language.lower() == "english":
        return text

    prompt = f"""Translate this {source_language} text to English.
Preserve the visual and descriptive meaning for image/video search.
Only output the translation, nothing else.

Text: {text}"""

    try:
        translation = await openai_client.complete(
            prompt=prompt,
            temperature=0.1,
            max_tokens=200,
        )
        return translation.strip()
    except Exception as e:
        logger.warning("translation_failed", error=str(e))
        return text


async def extract_search_terms(
    text: str,
    openai_client: OpenAIClient,
) -> list[str]:
    """Extract key search terms from text.

    Args:
        text: Input text
        openai_client: OpenAI client instance

    Returns:
        List of search terms
    """
    prompt = f"""Extract 3-5 key search terms from this text for image/video search.
Output only the terms, one per line.

Text: {text}"""

    try:
        result = await openai_client.complete(
            prompt=prompt,
            temperature=0.1,
            max_tokens=100,
        )
        terms = [t.strip() for t in result.strip().split("\n") if t.strip()]
        return terms[:5]
    except Exception as e:
        logger.warning("term_extraction_failed", error=str(e))
        return text.split()[:5]
