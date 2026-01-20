"""
Background Tasks - Redis Queue (RQ) task definitions

Tasks for processing documents and URLs in the background,
freeing the API to respond immediately.
"""

import os
import logging
import asyncio
from rq import Queue, Retry
from redis import Redis
from .config import settings
from .ingestion import ingest_pdf, ingest_txt

logger = logging.getLogger(__name__)

# Redis connection for RQ
redis_conn = Redis.from_url(settings.REDIS_URL)

# Task queue
task_queue = Queue('default', connection=redis_conn)

# Retry configuration: retry up to 3 times with exponential backoff
DEFAULT_RETRY = Retry(max=3, interval=[10, 60, 300])  # 10s, 1min, 5min


def process_file_task(file_path: str, filename: str, is_pdf: bool, user_id: str) -> dict:
    """
    Background task for processing uploaded files.

    Args:
        file_path: Path to the temporary file
        filename: Original filename
        is_pdf: Whether the file is a PDF
        user_id: User ID for PGVector collection

    Returns:
        dict with status and message
    """
    logger.info(f"Processing file '{filename}' for user {user_id}")

    try:
        if is_pdf:
            ingest_pdf(file_path, source=filename, user_id=user_id)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            ingest_txt(text, source=filename, user_id=user_id)

        logger.info(f"Successfully processed file '{filename}' for user {user_id}")
        return {"status": "completed", "message": f"Document '{filename}' indexed successfully"}

    except Exception as e:
        logger.error(f"Error processing file '{filename}' for user {user_id}: {e}")
        # Re-raise to trigger retry
        raise

    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temporary file: {file_path}")


def process_url_task(url: str, user_id: str) -> dict:
    """
    Background task for crawling and indexing URLs.

    Args:
        url: URL to crawl
        user_id: User ID for PGVector collection

    Returns:
        dict with status and message
    """
    logger.info(f"Processing URL '{url}' for user {user_id}")

    try:
        # Import here to avoid circular imports
        from .crawler import render_urls

        # Run async crawler in sync context
        docs = asyncio.run(render_urls([url]))
        text = "\n".join(d["page_content"] for d in docs)

        if not text.strip():
            logger.warning(f"No content extracted from URL '{url}'")
            return {"status": "failed", "message": "No content extracted from URL"}

        ingest_txt(text, source=url, user_id=user_id)

        logger.info(f"Successfully processed URL '{url}' for user {user_id}")
        return {"status": "completed", "message": f"URL '{url}' indexed successfully"}

    except Exception as e:
        logger.error(f"Error processing URL '{url}' for user {user_id}: {e}")
        # Re-raise to trigger retry
        raise


def enqueue_file_task(file_path: str, filename: str, is_pdf: bool, user_id: str) -> str:
    """
    Enqueue a file processing task.

    Returns:
        Job ID
    """
    job = task_queue.enqueue(
        process_file_task,
        file_path,
        filename,
        is_pdf,
        user_id,
        job_timeout='10m',  # 10 minutes timeout for large files
        meta={'user_id': user_id},  # Store user_id for ownership validation
        retry=DEFAULT_RETRY,  # Retry with exponential backoff
    )
    logger.info(f"Enqueued file task {job.id} for user {user_id}: {filename}")
    return job.id


def enqueue_url_task(url: str, user_id: str) -> str:
    """
    Enqueue a URL crawling task.

    Returns:
        Job ID
    """
    job = task_queue.enqueue(
        process_url_task,
        url,
        user_id,
        job_timeout='5m',  # 5 minutes timeout for crawling
        meta={'user_id': user_id},  # Store user_id for ownership validation
        retry=DEFAULT_RETRY,  # Retry with exponential backoff
    )
    logger.info(f"Enqueued URL task {job.id} for user {user_id}: {url}")
    return job.id


def get_job_status(job_id: str, user_id: str | None = None) -> dict:
    """
    Get the status of a job.

    Args:
        job_id: RQ job ID
        user_id: Optional user ID for ownership validation

    Returns:
        dict with job_id, status, result, and error if applicable

    Raises:
        Returns not_found if job doesn't belong to user (security)
    """
    from rq.job import Job

    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        return {
            "job_id": job_id,
            "status": "not_found",
            "result": None,
            "error": "Job not found"
        }

    # Validate ownership if user_id provided
    if user_id:
        job_user_id = job.meta.get('user_id')
        if job_user_id and job_user_id != user_id:
            # Don't reveal that job exists - return not_found for security
            return {
                "job_id": job_id,
                "status": "not_found",
                "result": None,
                "error": "Job not found"
            }

    status_map = {
        "queued": "queued",
        "started": "started",
        "deferred": "queued",
        "finished": "finished",
        "stopped": "failed",
        "scheduled": "queued",
        "canceled": "failed",
        "failed": "failed"
    }

    status = status_map.get(job.get_status(), "unknown")

    result = None
    error = None

    if status == "finished":
        result = job.result
    elif status == "failed":
        error = str(job.exc_info) if job.exc_info else "Unknown error"

    return {
        "job_id": job_id,
        "status": status,
        "result": result,
        "error": error
    }
