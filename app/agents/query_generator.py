"""Query generation agent using OpenAI."""

from typing import Any

from app.agents.base import BaseAgent
from app.models.query import GeneratedQuery, LanguageInfo
from app.multilingual.prompts import QUERY_GENERATION_SYSTEM, QUERY_GENERATION_USER_TEMPLATE
from app.services.cache import CacheService
from app.services.openai_client import OpenAIClient
from app.services.prompt_service import PromptService


class QueryInput:
    """Input for query generation."""

    def __init__(self, text: str, language_info: LanguageInfo):
        self.text = text
        self.language_info = language_info


class QueryGeneratorAgent(BaseAgent[QueryInput, GeneratedQuery]):
    """Agent for generating optimized search queries using OpenAI.

    Analyzes input text semantically and generates optimized queries
    for image/video search APIs.
    """

    name = "query_generator"
    cache_enabled = False
    cache_ttl = 3600

    def __init__(
        self,
        openai_client: OpenAIClient,
        cache: CacheService | None = None,
        prompt_service: PromptService | None = None,
    ):
        """Initialize query generator.

        Args:
            openai_client: OpenAI client for generation
            cache: Optional cache service
            prompt_service: Optional prompt service for dynamic prompts
        """
        super().__init__(cache)
        self.openai_client = openai_client
        self.prompt_service = prompt_service

    def _get_cache_key(self, input_data: QueryInput) -> str:
        """Generate cache key from input text."""
        from app.utils.hashing import generate_cache_key

        return generate_cache_key(
            self.name,
            input_data.text,
            input_data.language_info.code,
        )

    async def _get_prompts(self) -> tuple[str, str]:
        """Get system and user prompts.

        Returns:
            Tuple of (system_prompt, user_prompt_template)
        """
        if self.prompt_service is not None:
            system_prompt = await self.prompt_service.get_prompt("QUERY_GENERATION_SYSTEM")
            user_prompt = await self.prompt_service.get_prompt("QUERY_GENERATION_USER_TEMPLATE")
            return system_prompt, user_prompt
        # Fallback to hardcoded prompts
        return QUERY_GENERATION_SYSTEM, QUERY_GENERATION_USER_TEMPLATE

    async def process(self, input_data: QueryInput) -> GeneratedQuery:
        """Generate optimized search query.

        Args:
            input_data: Query input with text and language info

        Returns:
            GeneratedQuery with optimized queries
        """
        system_prompt, user_prompt_template = await self._get_prompts()

        prompt = user_prompt_template.format(
            text=input_data.text,
            language_name=input_data.language_info.name,
            language_code=input_data.language_info.code,
        )

        try:
            response = await self.openai_client.complete_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
            )

            return GeneratedQuery(
                original_text=input_data.text,
                english_query=response.get("english_query", input_data.text),
                native_query=response.get("native_query"),
                semantic_concepts=response.get("semantic_concepts", []),
                keywords=response.get("keywords", []),
                synonyms=response.get("synonyms", []),
                visual_elements=response.get("visual_elements", []),
                mood=response.get("mood"),
                style=response.get("style"),
                language_info=input_data.language_info,
            )

        except Exception as e:
            self.logger.error("query_generation_failed", error=str(e))
            # Return basic query on failure
            return self._fallback_query(input_data)

    def _fallback_query(self, input_data: QueryInput) -> GeneratedQuery:
        """Generate fallback query when OpenAI fails.

        Args:
            input_data: Original input

        Returns:
            Basic GeneratedQuery
        """
        # Extract simple keywords from text (len > 1 preserves short location abbreviations like NY, LA)
        words = input_data.text.split()
        keywords = [w.strip(".,!?") for w in words if len(w) > 1][:6]

        return GeneratedQuery(
            original_text=input_data.text,
            english_query=input_data.text if input_data.language_info.is_english else "",
            native_query=None if input_data.language_info.is_english else input_data.text,
            semantic_concepts=keywords,
            keywords=keywords,
            synonyms=[],
            visual_elements=[],
            mood=None,
            style=None,
            language_info=input_data.language_info,
        )

    def _deserialize_output(self, data: dict[str, Any]) -> GeneratedQuery:
        """Deserialize GeneratedQuery from cache."""
        return GeneratedQuery.model_validate(data)
