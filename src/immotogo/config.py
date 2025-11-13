"""Application settings for ImmoTogo AI."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration using environment variables."""

    model_config = SettingsConfigDict(env_file=('.env',), case_sensitive=False)

    environment: Literal["dev", "staging", "prod"] = Field(
        default="dev", description="Deployment environment tag"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Minimum log level for the application"
    )

    database_dsn: str = Field(
        default="mysql+pymysql://immotogo:immotogo@localhost:3306/immotogo",
        description="SQLAlchemy compatible DSN for the ingestion store",
    )
    chroma_persist_directory: Path = Field(
        default=Path(".chroma"),
        description="Local directory where ChromaDB persists vectors",
    )
    hf_mistral_model: str = Field(
        default="mistralai/Mistral-7B-Instruct-v0.3",
        description="Hugging Face model id for the generator",
    )
    hf_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Model id used to embed listing documents",
    )
    hf_token: str | None = Field(
        default=None,
        description="Optional Hugging Face access token for gated models",
    )
    crawl_concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of concurrent HTTP requests per crawler",
    )
    crawl_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout applied to HTTP operations when scraping",
    )
    mistral_max_output_tokens: int = Field(
        default=650,
        description="Maximum number of generated tokens per response",
    )
    mistral_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Sampling temperature for the Mistral generator",
    )
    mistral_top_p: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Top-p nucleus sampling parameter",
    )

    cache_directory: Path = Field(
        default=Path(".cache/immotogo"),
        description="Directory to cache downloaded models or artifacts",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""

    settings = Settings()
    settings.cache_directory.mkdir(parents=True, exist_ok=True)
    settings.chroma_persist_directory.mkdir(parents=True, exist_ok=True)
    return settings
