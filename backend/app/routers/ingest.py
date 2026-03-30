from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from ..security import require_auth
from ..clerk_auth import get_token_from_header, verify_clerk_token
from ..tasks import enqueue_file_task, enqueue_url_task
from ..crawler import is_safe_url
from ..pgvector_store import get_unique_source_count
import tempfile
import os
import threading
from slowapi import Limiter


def get_user_id_for_rate_limit(request: Request) -> str:
    """
    Extract user_id from Clerk JWT for rate limiting.
    Falls back to IP address if token is invalid/missing.
    """
    try:
        token = get_token_from_header(request)
        payload = verify_clerk_token(token)
        return f"user:{payload.get('sub', 'unknown')}"
    except Exception:
        # Fallback to IP if auth fails (rate limit will still apply)
        return f"ip:{request.client.host if request.client else 'unknown'}"


router = APIRouter(prefix="/ingest", tags=["ingest"])
limiter = Limiter(key_func=get_user_id_for_rate_limit)

# Limits for showcase app
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per file
from ..config import settings as app_settings
MAX_DOCUMENTS_PER_USER = app_settings.MAX_DOCUMENTS_PER_USER

# Per-user locks to prevent race conditions on document limit checks + enqueue
_user_locks: dict[str, threading.Lock] = {}
_user_locks_lock = threading.Lock()


def _get_user_lock(user_id: str) -> threading.Lock:
    """Get or create a per-user lock for document limit checks."""
    if user_id not in _user_locks:
        with _user_locks_lock:
            if user_id not in _user_locks:
                _user_locks[user_id] = threading.Lock()
    return _user_locks[user_id]


def _check_limit_and_enqueue_file(user_id: str, file_path: str, filename: str, is_pdf: bool) -> str:
    """Atomically check document limit and enqueue file task under lock."""
    user_lock = _get_user_lock(user_id)
    with user_lock:
        current_docs = get_unique_source_count(user_id)
        if current_docs >= MAX_DOCUMENTS_PER_USER:
            raise HTTPException(
                400,
                f"Document limit reached. Maximum {MAX_DOCUMENTS_PER_USER} documents allowed. "
                "Please reset your knowledge base to upload new documents."
            )
        return enqueue_file_task(file_path, filename, is_pdf, user_id)


def _check_limit_and_enqueue_url(user_id: str, url: str) -> str:
    """Atomically check document limit and enqueue URL task under lock."""
    user_lock = _get_user_lock(user_id)
    with user_lock:
        current_docs = get_unique_source_count(user_id)
        if current_docs >= MAX_DOCUMENTS_PER_USER:
            raise HTTPException(
                400,
                f"Document limit reached. Maximum {MAX_DOCUMENTS_PER_USER} documents allowed. "
                "Please reset your knowledge base to index new URLs."
            )
        return enqueue_url_task(url, user_id)


@router.post("/upload", status_code=202)
@limiter.limit("10/hour")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(require_auth)
):
    """
    Upload document for background indexing.

    Returns immediately with job_id. Use GET /jobs/{job_id} to check status.
    Requires Clerk JWT authentication.
    Rate limited to 10 uploads per hour per user.
    Maximum file size: 5MB. Maximum 5 documents per user.
    """
    filename = file.filename or "document.txt"
    is_pdf = filename.lower().endswith(".pdf")

    # Read and validate file size (outside lock — I/O bound)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")

    if len(content) == 0:
        raise HTTPException(400, "File is empty")

    # Validate file content matches extension
    if is_pdf and not content[:5].startswith(b"%PDF-"):
        raise HTTPException(400, "File content does not match PDF format")

    # Save file to temp location (will be deleted by worker after processing)
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        tmp.write(content)
        file_path = tmp.name

    try:
        # Atomically check limit + enqueue under per-user lock
        job_id = _check_limit_and_enqueue_file(user_id, file_path, filename, is_pdf)

        return JSONResponse(
            status_code=202,
            content={
                "ok": True,
                "job_id": job_id,
                "status": "queued",
                "message": f"Document '{filename}' queued for processing"
            }
        )
    except HTTPException:
        if os.path.exists(file_path):
            os.unlink(file_path)
        raise
    except Exception:
        if os.path.exists(file_path):
            os.unlink(file_path)
        raise HTTPException(500, "Error queuing document for processing")

@router.post("/crawl", status_code=202)
@limiter.limit("10/hour")
async def crawl(
    request: Request,
    url: str = Form(...),
    user_id: str = Depends(require_auth)
):
    """
    Queue URL for background crawling and indexing.

    Returns immediately with job_id. Use GET /jobs/{job_id} to check status.
    Requires Clerk JWT authentication.
    Rate limited to 10 crawls per hour per user.
    Maximum 5 documents per user.
    """
    # Validate URL before queuing (SSRF protection)
    is_valid, error_msg = is_safe_url(url)
    if not is_valid:
        raise HTTPException(400, f"URL blocked: {error_msg}")

    try:
        # Atomically check limit + enqueue under per-user lock
        job_id = _check_limit_and_enqueue_url(user_id, url)

        return JSONResponse(
            status_code=202,
            content={
                "ok": True,
                "job_id": job_id,
                "status": "queued",
                "message": f"URL '{url}' queued for indexing"
            }
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "Error queuing URL for processing")
