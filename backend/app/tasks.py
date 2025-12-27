"""
Background Tasks - Redis Queue (RQ) task definitions

Tasks for processing documents and URLs in the background,
freeing the API to respond immediately.
"""

import os
import asyncio
from rq import Queue
from redis import Redis
from .config import settings
from .ingestion import ingest_pdf, ingest_txt, embed_and_upsert, _to_vectors

# Redis connection for RQ
redis_conn = Redis.from_url(settings.REDIS_URL)

# Task queue
task_queue = Queue('default', connection=redis_conn)


def process_file_task(file_path: str, filename: str, is_pdf: bool, namespace: str) -> dict:
    """
    Background task for processing uploaded files.

    Args:
        file_path: Path to the temporary file
        filename: Original filename
        is_pdf: Whether the file is a PDF
        namespace: User's Pinecone namespace

    Returns:
        dict with status and message
    """
    try:
        if is_pdf:
            ingest_pdf(file_path, source=filename, namespace=namespace)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            ingest_txt(text, source=filename, namespace=namespace)

        return {"status": "completed", "message": f"Document '{filename}' indexed successfully"}

    except Exception as e:
        return {"status": "failed", "message": f"Error processing document: {str(e)}"}

    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.unlink(file_path)


def process_url_task(url: str, namespace: str) -> dict:
    """
    Background task for crawling and indexing URLs.

    Args:
        url: URL to crawl
        namespace: User's Pinecone namespace

    Returns:
        dict with status and message
    """
    try:
        # Import here to avoid circular imports
        from .crawler import render_urls

        # Run async crawler in sync context
        docs = asyncio.run(render_urls([url]))
        text = "\n".join(d["page_content"] for d in docs)

        if not text.strip():
            return {"status": "failed", "message": "No content extracted from URL"}

        vectors = _to_vectors(text, source=url)
        embed_and_upsert(vectors, namespace=namespace)

        return {"status": "completed", "message": f"URL '{url}' indexed successfully"}

    except Exception as e:
        return {"status": "failed", "message": f"Error indexing URL: {str(e)}"}


def enqueue_file_task(file_path: str, filename: str, is_pdf: bool, namespace: str) -> str:
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
        namespace,
        job_timeout='10m'  # 10 minutes timeout for large files
    )
    return job.id


def enqueue_url_task(url: str, namespace: str) -> str:
    """
    Enqueue a URL crawling task.

    Returns:
        Job ID
    """
    job = task_queue.enqueue(
        process_url_task,
        url,
        namespace,
        job_timeout='5m'  # 5 minutes timeout for crawling
    )
    return job.id


def get_job_status(job_id: str) -> dict:
    """
    Get the status of a job.

    Args:
        job_id: RQ job ID

    Returns:
        dict with job_id, status, result, and error if applicable
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
