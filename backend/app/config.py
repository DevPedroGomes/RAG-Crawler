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

    # ==== Clerk Authentication ====
    # JWKS URL for your Clerk instance (optional, defaults to Clerk API)
    CLERK_JWKS_URL: str = os.getenv("CLERK_JWKS_URL", "")
    # Comma-separated list of authorized parties (azp) - your frontend URLs
    # Example: "http://localhost:3000,https://myapp.com"
    CLERK_AUTHORIZED_PARTIES: str = os.getenv("CLERK_AUTHORIZED_PARTIES", "")

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
logger.info(f"Clerk authorized parties: {settings.CLERK_AUTHORIZED_PARTIES or 'not configured (accepting all)'}")
