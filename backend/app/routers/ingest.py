from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from ..security import require_auth
from ..tasks import enqueue_file_task, enqueue_url_task
from ..crawler import is_safe_url
import tempfile
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/ingest", tags=["ingest"])
limiter = Limiter(key_func=get_remote_address)

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
    Requires session cookie and CSRF token.
    """
    filename = file.filename or "document.txt"
    ext = filename.lower()
    is_pdf = ext.endswith(".pdf")

    # Save file to temp location (will be deleted by worker after processing)
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        content = await file.read()
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
        raise HTTPException(500, f"Error queuing document: {str(e)}")

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
    Requires session cookie and CSRF token.
    """
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
    except Exception as e:
        raise HTTPException(500, f"Error queuing URL: {str(e)}")
