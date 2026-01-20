"""
Embedding Cache Service using Redis.

Caches query embeddings to reduce OpenAI API calls and improve latency.
Uses SHA256 hash of query as cache key with configurable TTL.
"""
import hashlib
import json
import logging
from typing import Optional, List

from .redis_client import get_redis_client
from .config import settings

logger = logging.getLogger(__name__)

# Cache TTL from settings (default 1 hour)
CACHE_TTL = settings.EMBEDDING_CACHE_TTL


def _get_cache_key(query: str) -> str:
    """Generate cache key from query using SHA256 hash.

    Args:
        query: Search query text

    Returns:
        Cache key string prefixed with 'emb:'
    """
    query_hash = hashlib.sha256(query.strip().lower().encode()).hexdigest()[:32]
    return f"emb:{query_hash}"


def get_cached_embedding(query: str) -> Optional[List[float]]:
    """Get cached embedding for a query.

    Args:
        query: Search query text

    Returns:
        Cached embedding vector if exists, None otherwise
    """
    try:
        redis = get_redis_client()
        key = _get_cache_key(query)
        cached = redis.get(key)

        if cached:
            logger.debug(f"Embedding cache HIT for query: {query[:50]}...")
            return json.loads(cached)

        logger.debug(f"Embedding cache MISS for query: {query[:50]}...")
        return None

    except Exception as e:
        logger.warning(f"Embedding cache get error: {e}")
        return None


def cache_embedding(query: str, embedding: List[float], ttl: int = CACHE_TTL) -> bool:
    """Cache an embedding for a query.

    Args:
        query: Search query text
        embedding: Embedding vector to cache
        ttl: Time-to-live in seconds (default: 1 hour)

    Returns:
        True if cached successfully
    """
    try:
        redis = get_redis_client()
        key = _get_cache_key(query)
        redis.setex(key, ttl, json.dumps(embedding))
        logger.debug(f"Cached embedding for query: {query[:50]}...")
        return True

    except Exception as e:
        logger.warning(f"Embedding cache set error: {e}")
        return False


def invalidate_embedding_cache(query: str) -> bool:
    """Invalidate cached embedding for a query.

    Args:
        query: Search query text

    Returns:
        True if invalidated successfully
    """
    try:
        redis = get_redis_client()
        key = _get_cache_key(query)
        redis.delete(key)
        return True

    except Exception as e:
        logger.warning(f"Embedding cache invalidate error: {e}")
        return False


def get_embedding_cache_stats() -> dict:
    """Get embedding cache statistics.

    Returns:
        Dict with cache stats (keys count, TTL info)
    """
    try:
        redis = get_redis_client()

        # Count embedding cache keys
        cursor = 0
        count = 0
        while True:
            cursor, keys = redis.scan(cursor, match="emb:*", count=100)
            count += len(keys)
            if cursor == 0:
                break

        return {
            "cached_embeddings": count,
            "ttl_seconds": CACHE_TTL,
        }

    except Exception as e:
        logger.warning(f"Embedding cache stats error: {e}")
        return {"error": str(e)}
