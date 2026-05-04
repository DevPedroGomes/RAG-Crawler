"""
PGVector store for document embeddings with HYBRID SEARCH support.

Implements a two-stage retrieval pipeline:
1. Semantic Search: Vector similarity using pgvector (cosine distance)
2. Keyword Search: Full-text search using PostgreSQL ts_vector
3. Hybrid: Combines both with Reciprocal Rank Fusion (RRF)

This approach provides both high recall (semantic) and precision for exact terms (keyword).
"""
import logging
from functools import lru_cache
from typing import List, Dict, Any, Optional
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from sqlalchemy import text
from .config import settings
from .database import engine

logger = logging.getLogger(__name__)

# RRF constant (standard value from literature)
RRF_K = 60


def init_pgvector():
    """
    Initialize pgvector extension, create tables and indexes.
    Should be called on application startup.
    """
    with engine.connect() as conn:
        try:
            # Enable pgvector extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("pgvector extension enabled")

            # Create the collection table (stores collection metadata)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS langchain_pg_collection (
                    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) UNIQUE NOT NULL,
                    cmetadata JSONB
                )
            """))
            conn.commit()
            logger.info("langchain_pg_collection table created/verified")

            # Create the embedding table (stores vectors)
            # Using 1536 dimensions for text-embedding-3-small
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    collection_id UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
                    embedding vector(1536),
                    document TEXT,
                    cmetadata JSONB
                )
            """))
            conn.commit()
            logger.info("langchain_pg_embedding table created/verified")

            # Create HNSW index for faster similarity search
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS langchain_pg_embedding_hnsw_idx
                ON langchain_pg_embedding
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))
            conn.commit()
            logger.info("HNSW index created/verified")

            # Create index on collection_id for faster filtering
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS langchain_pg_embedding_collection_idx
                ON langchain_pg_embedding (collection_id)
            """))
            conn.commit()
            logger.info("Collection index created/verified")

            # Add tsvector column for full-text search if not exists
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'langchain_pg_embedding'
                        AND column_name = 'document_tsv'
                    ) THEN
                        ALTER TABLE langchain_pg_embedding
                        ADD COLUMN document_tsv tsvector
                        GENERATED ALWAYS AS (to_tsvector('english', COALESCE(document, ''))) STORED;
                    END IF;
                END $$;
            """))
            conn.commit()
            logger.info("Full-text search column created/verified")

            # Create GIN index for full-text search
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS langchain_pg_embedding_fts_idx
                ON langchain_pg_embedding
                USING gin (document_tsv)
            """))
            conn.commit()
            logger.info("Full-text search GIN index created/verified")

        except Exception as e:
            logger.error(f"Error initializing pgvector: {e}")
            raise  # Fail startup if we can't create tables


@lru_cache(maxsize=1)
def get_embeddings():
    """Get OpenAI embeddings model (cached)."""
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY
    )


@lru_cache(maxsize=32)
def get_vector_store(user_id: str) -> PGVector:
    """
    Get PGVector store for a specific user.
    Uses user_id as collection_name to isolate data per user.
    """
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=f"user_{user_id}",
        connection=settings.DATABASE_URL,
        use_jsonb=True,
    )


def delete_user_documents(user_id: str):
    """
    Delete all documents for a specific user.
    Equivalent to deleting a Pinecone namespace.
    """
    collection_name = f"user_{user_id}"

    with engine.connect() as conn:
        # Delete from langchain_pg_embedding table where collection matches
        conn.execute(
            text("""
                DELETE FROM langchain_pg_embedding
                WHERE collection_id IN (
                    SELECT uuid FROM langchain_pg_collection
                    WHERE name = :collection_name
                )
            """),
            {"collection_name": collection_name}
        )
        # Delete the collection itself
        conn.execute(
            text("DELETE FROM langchain_pg_collection WHERE name = :collection_name"),
            {"collection_name": collection_name}
        )
        conn.commit()


def _table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database."""
    result = conn.execute(
        text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table_name
            )
        """),
        {"table_name": table_name}
    )
    return result.scalar() or False


def get_document_count(user_id: str) -> int:
    """
    Get the count of indexed document chunks for a specific user.
    Returns 0 if no documents are found or table doesn't exist yet.
    """
    collection_name = f"user_{user_id}"

    with engine.connect() as conn:
        # Table may not exist if no documents have been uploaded yet
        if not _table_exists(conn, "langchain_pg_embedding"):
            return 0

        result = conn.execute(
            text("""
                SELECT COUNT(*) FROM langchain_pg_embedding
                WHERE collection_id IN (
                    SELECT uuid FROM langchain_pg_collection
                    WHERE name = :collection_name
                )
            """),
            {"collection_name": collection_name}
        )
        return result.scalar() or 0


def get_unique_source_count(user_id: str) -> int:
    """
    Get the count of unique documents (sources) for a specific user.
    This counts distinct source URLs/filenames, not chunks.
    Returns 0 if table doesn't exist yet.
    """
    collection_name = f"user_{user_id}"

    with engine.connect() as conn:
        # Table may not exist if no documents have been uploaded yet
        if not _table_exists(conn, "langchain_pg_embedding"):
            return 0

        result = conn.execute(
            text("""
                SELECT COUNT(DISTINCT cmetadata->>'source')
                FROM langchain_pg_embedding
                WHERE collection_id IN (
                    SELECT uuid FROM langchain_pg_collection
                    WHERE name = :collection_name
                )
            """),
            {"collection_name": collection_name}
        )
        return result.scalar() or 0


def _get_embedding_with_cache(query: str) -> List[float]:
    """Get embedding for a query, using cache if available.

    Args:
        query: Search query text

    Returns:
        Embedding vector (1536 dimensions)
    """
    from .embedding_cache import get_cached_embedding, cache_embedding

    # Try cache first
    cached = get_cached_embedding(query)
    if cached:
        return cached

    # Generate new embedding
    embeddings = get_embeddings()
    vector = embeddings.embed_query(query)

    # Cache for future use
    cache_embedding(query, vector)

    return vector


def search_semantic(
    query: str,
    user_id: str,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Semantic search using vector similarity.

    Args:
        query: Search query
        user_id: User ID for collection filtering
        top_k: Number of results to return

    Returns:
        List of results with id, content, metadata, and score
    """
    collection_name = f"user_{user_id}"

    # Get query embedding (with cache)
    query_vector = _get_embedding_with_cache(query)

    with engine.connect() as conn:
        if not _table_exists(conn, "langchain_pg_embedding"):
            return []

        # Semantic search using cosine distance.
        # NOTE: SQLAlchemy named-params (`:name`) collide with Postgres' `::cast`
        # syntax inside text() — both use the colon. We use the SQL standard
        # CAST(... AS ...) form to avoid the ambiguity.
        result = conn.execute(
            text("""
                SELECT
                    e.id,
                    e.document as content,
                    e.cmetadata as metadata,
                    1 - (e.embedding <=> CAST(:query_vector AS vector)) as score
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = :collection_name
                ORDER BY e.embedding <=> CAST(:query_vector AS vector)
                LIMIT :top_k
            """),
            {
                "query_vector": str(query_vector),
                "collection_name": collection_name,
                "top_k": top_k
            }
        )

        return [
            {
                "id": str(row.id),
                "content": row.content,
                "metadata": row.metadata or {},
                "score": float(row.score) if row.score else 0.0,
            }
            for row in result.fetchall()
        ]


def search_keyword(
    query: str,
    user_id: str,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Keyword search using PostgreSQL full-text search.

    Args:
        query: Search query
        user_id: User ID for collection filtering
        top_k: Number of results to return

    Returns:
        List of results with id, content, metadata, and score
    """
    collection_name = f"user_{user_id}"

    # Convert query to tsquery format (handles multiple words)
    # plainto_tsquery converts plain text to tsquery
    with engine.connect() as conn:
        if not _table_exists(conn, "langchain_pg_embedding"):
            return []

        # Check if document_tsv column exists
        col_check = conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'langchain_pg_embedding'
                    AND column_name = 'document_tsv'
                )
            """)
        )
        if not col_check.scalar():
            logger.warning("document_tsv column not found, skipping keyword search")
            return []

        # Full-text search with ranking
        result = conn.execute(
            text("""
                SELECT
                    e.id,
                    e.document as content,
                    e.cmetadata as metadata,
                    ts_rank_cd(e.document_tsv, plainto_tsquery('english', :query)) as score
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = :collection_name
                AND e.document_tsv @@ plainto_tsquery('english', :query)
                ORDER BY score DESC
                LIMIT :top_k
            """),
            {
                "query": query,
                "collection_name": collection_name,
                "top_k": top_k
            }
        )

        return [
            {
                "id": str(row.id),
                "content": row.content,
                "metadata": row.metadata or {},
                "score": float(row.score) if row.score else 0.0,
            }
            for row in result.fetchall()
        ]


def _reciprocal_rank_fusion(
    results_list: List[List[Dict[str, Any]]],
    k: int = RRF_K,
) -> List[Dict[str, Any]]:
    """Combine multiple result lists using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank)) for each list where doc appears.

    Args:
        results_list: List of result lists from different search methods
        k: RRF constant (default: 60)

    Returns:
        Merged and re-ranked results
    """
    scores: Dict[str, Dict[str, Any]] = {}

    for results in results_list:
        for rank, doc in enumerate(results):
            doc_id = doc["id"]
            rrf_score = 1.0 / (k + rank + 1)

            if doc_id not in scores:
                scores[doc_id] = {
                    "id": doc_id,
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": 0.0,
                }
            scores[doc_id]["score"] += rrf_score

    # Sort by combined RRF score
    sorted_results = sorted(
        scores.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    return sorted_results


def search_hybrid(
    query: str,
    user_id: str,
    top_k: int = 5,
    semantic_weight: float = 0.7,
) -> List[Document]:
    """Hybrid search combining semantic and keyword search with RRF.

    This provides the best of both worlds:
    - Semantic: Understands meaning, synonyms, context
    - Keyword: Exact matches for technical terms, codes, IDs

    Args:
        query: Search query
        user_id: User ID for collection filtering
        top_k: Final number of results to return
        semantic_weight: Not used with RRF, kept for API compatibility

    Returns:
        List of LangChain Document objects with metadata
    """
    # Fetch more candidates for RRF to work with
    fetch_k = top_k * 3

    # Run both searches
    semantic_results = search_semantic(query, user_id, top_k=fetch_k)
    keyword_results = search_keyword(query, user_id, top_k=fetch_k)

    logger.debug(f"Hybrid search: {len(semantic_results)} semantic, {len(keyword_results)} keyword results")

    # Combine with RRF
    if keyword_results:
        merged = _reciprocal_rank_fusion([semantic_results, keyword_results])
    else:
        # Fallback to semantic only if no keyword matches
        merged = semantic_results

    # Convert to LangChain Documents and limit to top_k
    documents = []
    for result in merged[:top_k]:
        doc = Document(
            page_content=result["content"],
            metadata={
                **result["metadata"],
                "relevance_score": result["score"],
            }
        )
        documents.append(doc)

    return documents


def search_documents(
    query: str,
    user_id: str,
    top_k: int = 5,
    use_hybrid: Optional[bool] = None,
) -> List[Document]:
    """Main search function - uses hybrid search by default based on settings.

    Args:
        query: Search query
        user_id: User ID for collection filtering
        top_k: Number of results to return
        use_hybrid: Whether to use hybrid search (default: uses ENABLE_HYBRID_SEARCH setting)

    Returns:
        List of LangChain Document objects
    """
    # Use setting if not explicitly specified
    if use_hybrid is None:
        use_hybrid = settings.ENABLE_HYBRID_SEARCH

    if use_hybrid:
        return search_hybrid(query, user_id, top_k)
    else:
        # Semantic-only search using the existing PGVector retriever
        vs = get_vector_store(user_id)
        retriever = vs.as_retriever(
            search_type="mmr",
            search_kwargs={"k": top_k, "fetch_k": 25, "lambda_mult": 0.5}
        )
        return retriever.invoke(query)
