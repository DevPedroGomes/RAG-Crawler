"""
Background Tasks - Periodic maintenance tasks

Includes automatic cleanup of inactive user documents (showcase mode).
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from .user_activity import cleanup_inactive_users

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Returns scheduler (singleton)"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def _run_cleanup():
    """Run the inactive user cleanup task."""
    try:
        cleaned = cleanup_inactive_users()
        if cleaned > 0:
            logger.info(f"[Cleanup Task] Cleaned up documents for {cleaned} inactive users")
    except Exception as e:
        logger.error(f"[Cleanup Task] Error during cleanup: {e}")


def start_background_tasks():
    """
    Start background tasks.

    - Inactive user cleanup: Runs every minute to clean up documents
      for users inactive for more than 10 minutes (showcase mode).
    """
    scheduler = get_scheduler()

    # Add cleanup job - runs every minute
    scheduler.add_job(
        _run_cleanup,
        'interval',
        minutes=1,
        id='inactive_user_cleanup',
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )

    scheduler.start()
    logger.info("[Background Tasks] Scheduler started with inactive user cleanup (every 1 minute)")


def stop_background_tasks():
    """Stop all background tasks"""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("[Background Tasks] Scheduler stopped")
