"""
Analysis Router - Search comparison and embedding visualization endpoints.

Provides transparency into the RAG pipeline for the showcase UI.
"""
import logging
import json
from fastapi import APIRouter, Request, Depends, Body
from ..security import require_auth
from ..schemas import ChatIn
from ..pgvector_store import (
    search_semantic, search_keyword, search_hybrid,
    get_document_count, _get_embedding_with_cache,
)
from ..config import settings
from ..database import engine
from sqlalchemy import text
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/search-comparison")
@limiter.limit("20/minute")
def search_comparison(
    request: Request,
    payload: ChatIn = Body(...),
    user_id: str = Depends(require_auth),
):
    """
    Run semantic, keyword, and hybrid searches side-by-side
    so the UI can show the user how each method works.

    Returns results from all three search strategies with scores.
    """
    question = payload.question
    top_k = settings.TOP_K
    fetch_k = top_k * 3

    semantic_results = search_semantic(question, user_id, top_k=fetch_k)
    keyword_results = search_keyword(question, user_id, top_k=fetch_k)
    hybrid_docs = search_hybrid(question, user_id, top_k=top_k)

    def _fmt(results, limit=top_k):
        return [
            {
                "content": r["content"][:200] + ("..." if len(r["content"]) > 200 else ""),
                "source": r["metadata"].get("source", ""),
                "score": round(r["score"], 4),
            }
            for r in results[:limit]
        ]

    def _fmt_hybrid(docs):
        return [
            {
                "content": d.page_content[:200] + ("..." if len(d.page_content) > 200 else ""),
                "source": d.metadata.get("source", ""),
                "score": round(d.metadata.get("relevance_score", 0), 4),
            }
            for d in docs
        ]

    return {
        "semantic": _fmt(semantic_results),
        "keyword": _fmt(keyword_results),
        "hybrid": _fmt_hybrid(hybrid_docs),
        "meta": {
            "semantic_total": len(semantic_results),
            "keyword_total": len(keyword_results),
            "hybrid_total": len(hybrid_docs),
        },
    }


@router.get("/embeddings-2d")
@limiter.limit("10/minute")
def get_embeddings_2d(
    request: Request,
    user_id: str = Depends(require_auth),
):
    """
    Return a 2D projection of all document chunk embeddings for the user.

    Uses PCA for dimensionality reduction (1536 -> 2 dimensions).
    Returns points with x, y coordinates, source label, and a text preview.
    """
    collection_name = f"user_{user_id}"

    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    e.embedding::text as embedding_str,
                    LEFT(e.document, 120) as preview,
                    e.cmetadata->>'source' as source
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = :collection_name
                LIMIT 200
            """),
            {"collection_name": collection_name},
        )
        rows = result.fetchall()

    if len(rows) < 2:
        return {"points": [], "message": "Need at least 2 chunks for visualization"}

    # Parse embedding vectors
    import numpy as np

    vectors = []
    points_meta = []
    for row in rows:
        try:
            vec = json.loads(row.embedding_str)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Skipping chunk with unparseable embedding")
            continue
        vectors.append(vec)
        points_meta.append({
            "preview": row.preview + ("..." if len(row.preview) >= 120 else ""),
            "source": row.source or "unknown",
        })

    if len(vectors) < 2:
        return {"points": [], "message": "Need at least 2 valid chunks for visualization"}

    vectors_np = np.array(vectors)

    # PCA to 2D
    mean = vectors_np.mean(axis=0)
    centered = vectors_np - mean
    # SVD-based PCA (no sklearn needed)
    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    projected = centered @ Vt[:2].T

    # Normalize to 0-100 range for easy rendering
    for dim in range(2):
        col = projected[:, dim]
        mn, mx = col.min(), col.max()
        if mx - mn > 0:
            projected[:, dim] = (col - mn) / (mx - mn) * 100

    points = []
    for i, meta in enumerate(points_meta):
        points.append({
            "x": round(float(projected[i, 0]), 2),
            "y": round(float(projected[i, 1]), 2),
            "preview": meta["preview"],
            "source": meta["source"],
        })

    return {"points": points}
