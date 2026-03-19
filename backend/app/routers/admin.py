"""
Admin Router - User Data Management

Clerk handles authentication (logout via frontend).
This router provides data management operations.
"""
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from ..security import require_auth
from ..pgvector_store import delete_user_documents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/clear-data")
def clear_user_data(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """
    Clears all user data (documents) from the knowledge base.

    User session/logout is handled by Clerk on the frontend.
    This endpoint only clears RAG data.
    """
    try:
        delete_user_documents(user_id)
        return {"ok": True, "message": "User data cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing data for user {user_id}: {e}", exc_info=True)
        raise HTTPException(500, "Error clearing data. Please try again.")
