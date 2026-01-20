"""
Jobs Router - Endpoints for checking background job status
"""

from fastapi import APIRouter, Request, Depends
from ..security import require_auth
from ..tasks import get_job_status

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(
    job_id: str,
    request: Request,
    user_id: str = Depends(require_auth)
):
    """
    Get the status of a background job.

    Returns:
        - job_id: The job identifier
        - status: "queued" | "started" | "finished" | "failed" | "not_found"
        - result: Job result (if finished)
        - error: Error message (if failed)

    Requires Clerk JWT authentication.
    Jobs are only visible to the user who created them.
    """
    # Pass user_id to validate job ownership
    return get_job_status(job_id, user_id=user_id)
