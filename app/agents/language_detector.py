"""Language detection agent."""

from typing import Any

from app.agents.base import BaseAgent
from app.models.query import LanguageInfo
from app.multilingual.detector import detect_language
from app.services.cache import CacheService
from app.services.openai_client import OpenAIClient


class LanguageDetectorAgent(BaseAgent[str, LanguageInfo]):
    """Agent for detecting language of input text.

    Uses langdetect library for fast detection with OpenAI fallback
    for ambiguous cases.
    """

    name = "language_detector"
    cache_enabled = True
    cache_ttl = 86400  # Cache language detection for 24 hours

    def __init__(
        self,
        cache: CacheService | None = None,
        openai_client: OpenAIClient | None = None,
        confidence_threshold: float = 0.8,
    ):
        """Initialize language detector.

        Args:
            cache: Optional cache service
            openai_client: Optional OpenAI client for fallback
            confidence_threshold: Threshold for using OpenAI fallback
        """
        super().__init__(cache)
        self.openai_client = openai_client
        self.confidence_threshold = confidence_threshold

    async def process(self, text: str) -> LanguageInfo:
        """Detect language of input text.

        Args:
            text: Input text to analyze

        Returns:
            LanguageInfo with detection results
        """
        # Primary detection using langdetect
        result = detect_language(text)

        # Use OpenAI fallback for low confidence
        if result.confidence < self.confidence_threshold and self.openai_client:
            self.logger.info(
                "using_openai_fallback",
                initial_confidence=result.confidence,
            )
            result = await self._openai_detect(text, result)

        return result

    async def _openai_detect(
        self,
        text: str,
        initial_result: LanguageInfo,
    ) -> LanguageInfo:
        """Use OpenAI for more accurate language detection.

        Args:
            text: Input text
            initial_result: Initial detection result

        Returns:
            Updated LanguageInfo
        """
        if not self.openai_client:
            return initial_result

        try:
            prompt = f"""Identify the language of this text. Respond with JSON only:
{{"code": "ISO 639-1 code", "name": "Language name", "confidence": 0.0-1.0}}

Text: {text[:500]}"""

            response = await self.openai_client.complete_json(prompt, temperature=0.1)

            return LanguageInfo(
                code=response.get("code", initial_result.code),
                name=response.get("name", initial_result.name),
                confidence=response.get("confidence", 0.9),
                is_english=response.get("code", "").lower() == "en",
            )

        except Exception as e:
            self.logger.warning("openai_detection_failed", error=str(e))
            return initial_result

    def _deserialize_output(self, data: dict[str, Any]) -> LanguageInfo:
        """Deserialize LanguageInfo from cache."""
        return LanguageInfo.model_validate(data)
