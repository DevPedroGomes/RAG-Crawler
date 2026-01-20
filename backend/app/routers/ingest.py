from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from ..security import require_auth
from ..clerk_auth import get_token_from_header, verify_clerk_token
from ..tasks import enqueue_file_task, enqueue_url_task
from ..crawler import is_safe_url
from ..pgvector_store import get_unique_source_count
import tempfile
import os
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
MAX_DOCUMENTS_PER_USER = 5  # Maximum 5 documents per user


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
    # Check document limit
    current_docs = get_unique_source_count(user_id)
    if current_docs >= MAX_DOCUMENTS_PER_USER:
        raise HTTPException(
            400,
            f"Document limit reached. Maximum {MAX_DOCUMENTS_PER_USER} documents allowed. "
            "Please reset your knowledge base to upload new documents."
        )

    filename = file.filename or "document.txt"
    ext = filename.lower()
    is_pdf = ext.endswith(".pdf")

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")

    if len(content) == 0:
        raise HTTPException(400, "File is empty")

    # Save file to temp location (will be deleted by worker after processing)
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        tmp.write(content)
        file_path = tmp.name

    try:
        # Enqueue task for background processing
        job_id = enqueue_file_task(file_path, filename, is_pdf, user_id)

        return JSONResponse(
            status_code=202,
            content={
                "ok": True,
                "job_id": job_id,
                "status": "queued",
                "message": f"Document '{filename}' queued for processing"
            }
        )
    except Exception as e:
        # Clean up file if enqueueing fails
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
    # Check document limit
    current_docs = get_unique_source_count(user_id)
    if current_docs >= MAX_DOCUMENTS_PER_USER:
        raise HTTPException(
            400,
            f"Document limit reached. Maximum {MAX_DOCUMENTS_PER_USER} documents allowed. "
            "Please reset your knowledge base to index new URLs."
        )

    # Validate URL before queuing (SSRF protection)
    is_valid, error_msg = is_safe_url(url)
    if not is_valid:
        raise HTTPException(400, f"URL blocked: {error_msg}")

    try:
        # Enqueue task for background processing
        job_id = enqueue_url_task(url, user_id)

        return JSONResponse(
            status_code=202,
            content={
                "ok": True,
                "job_id": job_id,
                "status": "queued",
                "message": f"URL '{url}' queued for indexing"
            }
        )
    except Exception:
        raise HTTPException(500, "Error queuing URL for processing")
