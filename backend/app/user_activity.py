"""
User Activity Tracking and Automatic Cleanup

Tracks user activity and automatically cleans up documents
for inactive users (showcase mode - 10 minutes inactivity).
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from .redis_client import get_redis_client
from .pgvector_store import delete_user_documents, get_unique_source_count

logger = logging.getLogger(__name__)

# Inactivity timeout for document cleanup (10 minutes)
INACTIVITY_TIMEOUT_MINUTES = 10

# Redis key prefix for user activity
ACTIVITY_KEY_PREFIX = "user_activity:"


def update_user_activity(user_id: str) -> None:
    """
    Update the last activity timestamp for a user.
    Should be called on every authenticated request.
    """
    try:
        client = get_redis_client()
        key = f"{ACTIVITY_KEY_PREFIX}{user_id}"
        timestamp = datetime.utcnow().isoformat()

        # Set activity timestamp with expiration slightly longer than timeout
        # This ensures keys are automatically cleaned up if not accessed
        expiration_seconds = (INACTIVITY_TIMEOUT_MINUTES + 5) * 60
        client.setex(key, expiration_seconds, timestamp)

        logger.debug(f"Updated activity for user {user_id[:8]}...")
    except Exception as e:
        # Don't fail the request if activity tracking fails
        logger.warning(f"Failed to update user activity: {e}")


def get_user_last_activity(user_id: str) -> Optional[datetime]:
    """Get the last activity timestamp for a user."""
    try:
        client = get_redis_client()
        key = f"{ACTIVITY_KEY_PREFIX}{user_id}"
        timestamp_str = client.get(key)

        if timestamp_str:
            return datetime.fromisoformat(timestamp_str)
        return None
    except Exception as e:
        logger.warning(f"Failed to get user activity: {e}")
        return None


def get_all_active_users() -> List[str]:
    """Get list of all users with activity records."""
    try:
        client = get_redis_client()
        keys = client.keys(f"{ACTIVITY_KEY_PREFIX}*")
        return [key.replace(ACTIVITY_KEY_PREFIX, "") for key in keys]
    except Exception as e:
        logger.warning(f"Failed to get active users: {e}")
        return []


def cleanup_inactive_users() -> int:
    """
    Clean up documents for users who have been inactive for more than
    INACTIVITY_TIMEOUT_MINUTES.

    Returns the number of users cleaned up.
    """
    cleaned_count = 0
    cutoff_time = datetime.utcnow() - timedelta(minutes=INACTIVITY_TIMEOUT_MINUTES)

    try:
        client = get_redis_client()
        active_users = get_all_active_users()

        for user_id in active_users:
            last_activity = get_user_last_activity(user_id)

            if last_activity and last_activity < cutoff_time:
                # Check if user has documents before cleaning
                doc_count = get_unique_source_count(user_id)

                if doc_count > 0:
                    logger.info(
                        f"Cleaning up {doc_count} documents for inactive user {user_id[:8]}... "
                        f"(last active: {last_activity.isoformat()})"
                    )

                    try:
                        delete_user_documents(user_id)
                        cleaned_count += 1
                        logger.info(f"Successfully cleaned up documents for user {user_id[:8]}...")
                    except Exception as e:
                        logger.error(f"Failed to clean up documents for user {user_id[:8]}...: {e}")

                # Remove the activity key after cleanup
                key = f"{ACTIVITY_KEY_PREFIX}{user_id}"
                client.delete(key)

        if cleaned_count > 0:
            logger.info(f"Cleanup complete: {cleaned_count} users cleaned up")

    except Exception as e:
        logger.error(f"Error during inactive user cleanup: {e}")

    return cleaned_count


def cleanup_user_on_logout(user_id: str) -> bool:
    """
    Clean up documents for a user when they explicitly log out.
    Also removes their activity tracking.
    """
    try:
        # Delete documents
        delete_user_documents(user_id)

        # Remove activity tracking
        client = get_redis_client()
        key = f"{ACTIVITY_KEY_PREFIX}{user_id}"
        client.delete(key)

        logger.info(f"Cleaned up documents on logout for user {user_id[:8]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to clean up on logout for user {user_id[:8]}...: {e}")
        return False
