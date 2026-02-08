"""OpenAI API client wrapper."""

import json
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.exceptions import ExternalServiceError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """Wrapper for OpenAI API with structured output support."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        max_tokens: int = 1000,
        temperature: float = 0.3,
    ):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model for text generation
            embedding_model: Model for embeddings
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
        """
        self.model = model
        self.embedding_model = embedding_model
        self.max_tokens = max_tokens
        self.temperature = temperature

        self._client = AsyncOpenAI(api_key=api_key)
        self._api_key = api_key

    @property
    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return bool(self._api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate text completion.

        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            Generated text

        Raises:
            ExternalServiceError: On API failure
        """
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )

            content = response.choices[0].message.content
            if content is None:
                raise ExternalServiceError(
                    message="Empty response from OpenAI",
                    service="openai",
                )
            return content

        except Exception as e:
            logger.error("openai_completion_failed", error=str(e))
            raise ExternalServiceError(
                message=f"OpenAI completion failed: {e}",
                service="openai",
                details={"error": str(e)},
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def complete_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Generate JSON completion.

        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Override temperature

        Returns:
            Parsed JSON response

        Raises:
            ExternalServiceError: On API or parsing failure
        """
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.info(
            "openai_request",
            system_prompt=system_prompt[:200] if system_prompt else None,
            user_prompt=prompt[:500],
        )

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content is None:
                raise ExternalServiceError(
                    message="Empty response from OpenAI",
                    service="openai",
                )

            logger.info(
                "openai_response",
                response=content[:1000],
            )

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error("openai_json_parse_failed", error=str(e))
            raise ExternalServiceError(
                message=f"Failed to parse OpenAI JSON response: {e}",
                service="openai",
                details={"error": str(e)},
            )
        except Exception as e:
            logger.error("openai_json_completion_failed", error=str(e))
            raise ExternalServiceError(
                message=f"OpenAI JSON completion failed: {e}",
                service="openai",
                details={"error": str(e)},
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            ExternalServiceError: On API failure
        """
        try:
            response = await self._client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error("openai_embedding_failed", error=str(e))
            raise ExternalServiceError(
                message=f"OpenAI embedding failed: {e}",
                service="openai",
                details={"error": str(e)},
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            ExternalServiceError: On API failure
        """
        if not texts:
            return []

        try:
            response = await self._client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]

        except Exception as e:
            logger.error("openai_batch_embedding_failed", error=str(e))
            raise ExternalServiceError(
                message=f"OpenAI batch embedding failed: {e}",
                service="openai",
                details={"error": str(e)},
            )
