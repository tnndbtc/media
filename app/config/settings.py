"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: SecretStr = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model for text generation")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI model for embeddings"
    )
    openai_max_tokens: int = Field(default=1000, ge=100, le=4000)
    openai_temperature: float = Field(default=0.3, ge=0.0, le=2.0)

    # Pexels API
    pexels_api_key: SecretStr = Field(..., description="Pexels API key")
    pexels_base_url: str = Field(default="https://api.pexels.com/v1")

    # Pixabay API
    pixabay_api_key: SecretStr = Field(..., description="Pixabay API key")
    pixabay_base_url: str = Field(default="https://pixabay.com/api")

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_password: SecretStr | None = Field(default=None)

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./data/prompts.db",
        description="SQLite database URL for prompt storage",
    )

    # Cache Settings
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    cache_enabled: bool = Field(default=True)

    # API Settings
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = Field(default=False)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="DEBUG")

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    # Search Defaults
    default_search_limit: int = Field(default=20, ge=1, le=100)
    max_search_limit: int = Field(default=100, ge=1, le=500)
    max_batch_size: int = Field(default=10, ge=1, le=50)

    # HTTP Client Settings
    http_timeout_seconds: float = Field(default=30.0, ge=5.0, le=120.0)
    http_max_retries: int = Field(default=3, ge=0, le=10)

    # Ranking Weights
    weight_semantic_relevance: float = Field(default=0.35, ge=0.0, le=1.0)
    weight_keyword_match: float = Field(default=0.20, ge=0.0, le=1.0)
    weight_visual_quality: float = Field(default=0.15, ge=0.0, le=1.0)
    weight_popularity: float = Field(default=0.10, ge=0.0, le=1.0)
    weight_recency: float = Field(default=0.10, ge=0.0, le=1.0)
    weight_source_diversity: float = Field(default=0.10, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
