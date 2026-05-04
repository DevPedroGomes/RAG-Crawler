"""
Application Settings

All configuration is loaded from environment variables.
Required variables will cause startup failure if missing.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # ==== Required Settings (will fail if missing) ====
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # ==== LLM Provider (chat completions only) ====
    # OpenAI-compatible. When LLM_PROVIDER=openrouter, the chat client points at
    # OpenRouter and LLM_MODEL is the OpenRouter id (e.g. "deepseek/deepseek-chat").
    # Embeddings ALWAYS go through OpenAI (OpenRouter does not host embeddings).
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # ==== Better Auth ====
    # Sessions live in Postgres (managed by the Next.js frontend). The Python
    # backend reads the cookie ``__Secure-better-auth.session_token`` (or its
    # non-secure variant) and resolves the user via SQL — see app/auth.py.
    # No secret is needed here because we don't sign anything; we only read.

    # ==== RAG Settings ====
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1200"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K: int = int(os.getenv("TOP_K", "5"))

    # ==== Hybrid Search Settings ====
    ENABLE_HYBRID_SEARCH: bool = os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true"
    EMBEDDING_CACHE_TTL: int = int(os.getenv("EMBEDDING_CACHE_TTL", "3600"))  # 1 hour default

    # ==== Crawler Settings ====
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "12"))
    CRAWL_DELAY_MS: int = int(os.getenv("CRAWL_DELAY_MS", "0"))
    USER_AGENT: str = os.getenv("USER_AGENT", "RAGCrawler/1.0 (+https://github.com/)")

    # ==== Application Settings ====
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_DOCUMENTS_PER_USER: int = int(os.getenv("MAX_DOCUMENTS_PER_USER", "5"))

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        if not v:
            raise ValueError("OPENAI_API_KEY is required")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v:
            raise ValueError("REDIS_URL is required")
        return v


settings = Settings()

# Log configuration on startup (without secrets)
logger.info(f"Environment: {settings.ENVIRONMENT}")
logger.info(f"Database configured: {bool(settings.DATABASE_URL)}")
logger.info(f"Redis configured: {bool(settings.REDIS_URL)}")
logger.info("Auth: Better Auth (cookie-based sessions via shared Postgres)")
