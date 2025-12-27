from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "my-multiuser-index")
    PINECONE_INDEX_HOST: str = os.getenv("PINECONE_INDEX_HOST", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me")
    JWT_ALG: str = os.getenv("JWT_ALG", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1200"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K: int = int(os.getenv("TOP_K", "5"))
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "12"))
    CRAWL_DELAY_MS: int = int(os.getenv("CRAWL_DELAY_MS", "0"))
    USER_AGENT: str = os.getenv("USER_AGENT", "pg-multi-crawler/1.0")

settings = Settings()
