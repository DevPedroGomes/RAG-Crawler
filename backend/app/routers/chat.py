import logging
from fastapi import APIRouter, HTTPException, Body, Request, Depends
from fastapi.responses import StreamingResponse
from ..security import require_auth
from ..schemas import ChatIn, DocumentCountOut
from ..rag import answer, answer_stream
from ..pgvector_store import delete_user_documents, get_document_count, get_unique_source_count
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
limiter = Limiter(key_func=get_remote_address)


from ..config import settings

MAX_DOCUMENTS_PER_USER = settings.MAX_DOCUMENTS_PER_USER


@router.get("/documents", response_model=DocumentCountOut)
def get_documents(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """
    Get the count of indexed documents for the current user.
    Used to check if user can start chatting and show limits.
    """
    try:
        chunk_count = get_document_count(user_id)
        source_count = get_unique_source_count(user_id)
        return DocumentCountOut(
            count=chunk_count,
            has_documents=chunk_count > 0,
            documents_used=source_count,
            documents_limit=MAX_DOCUMENTS_PER_USER,
            can_upload=source_count < MAX_DOCUMENTS_PER_USER
        )
    except Exception as e:
        logger.error(f"Error getting document count: {e}")
        return DocumentCountOut(count=0, has_documents=False)


@router.post("/ask")
@limiter.limit("20/minute")
def ask(
    request: Request,
    payload: ChatIn = Body(...),
    user_id: str = Depends(require_auth)
):
    """
    Ask a question to the RAG system with conversation history.

    The chat_history parameter allows the LLM to maintain context
    across multiple turns of conversation.

    Requires Clerk JWT authentication.
    """
    try:
        # Convert chat history to list of dicts
        chat_history = None
        if payload.chat_history:
            chat_history = [{"role": m.role, "content": m.content} for m in payload.chat_history]

        result = answer(
            question=payload.question,
            user_id=user_id,
            chat_history=chat_history
        )
        return result
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(500, "Error processing your question. Please try again.")


@router.post("/ask/stream")
@limiter.limit("20/minute")
def ask_stream(
    request: Request,
    payload: ChatIn = Body(...),
    user_id: str = Depends(require_auth)
):
    """
    Stream an answer from the RAG system via Server-Sent Events.

    Events:
      - sources: JSON array of source objects (sent first)
      - token: text chunk from the LLM
      - done: signals stream is complete
      - error: error message
    """
    chat_history = None
    if payload.chat_history:
        chat_history = [{"role": m.role, "content": m.content} for m in payload.chat_history]

    return StreamingResponse(
        answer_stream(
            question=payload.question,
            user_id=user_id,
            chat_history=chat_history,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/reset")
def reset(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """
    Delete all indexed documents for the current user.

    Requires Clerk JWT authentication.
    """
    try:
        delete_user_documents(user_id)
        return {"ok": True, "message": "Knowledge base reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting knowledge base: {e}")
        raise HTTPException(500, "Error resetting knowledge base. Please try again.")
