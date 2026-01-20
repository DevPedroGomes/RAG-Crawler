"""
Auth Router - Clerk Integration

Clerk handles all authentication (signup, login, logout) via frontend components.
This router only provides a way to verify the current user.
"""
from fastapi import APIRouter, Depends
from ..clerk_auth import require_clerk_auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def get_current_user(user_id: str = Depends(require_clerk_auth)):
    """
    Returns current authenticated user info.

    Clerk handles login/signup/logout via frontend components.
    This endpoint verifies the JWT and returns the user ID.
    """
    return {
        "ok": True,
        "user_id": user_id,
        "message": "Authenticated via Clerk"
    }
