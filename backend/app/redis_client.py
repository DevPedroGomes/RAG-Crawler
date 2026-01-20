"""
Redis Client Module.

Provides a singleton Redis client connection for the application.
Used by: embedding_cache, user_activity, and other services.
"""
import logging
from functools import lru_cache
import redis

from .config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    """Get Redis client instance (singleton).

    Returns:
        Redis client connected to the configured REDIS_URL
    """
    client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True
    )
    logger.info("Redis client initialized")
    return client


def check_redis_connection() -> bool:
    """Check if Redis connection is healthy.

    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection check failed: {e}")
        return False
