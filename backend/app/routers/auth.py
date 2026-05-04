"""
Auth Router — Better Auth bridge.

Better Auth handles signup/login/logout in the Next.js frontend. This
router only verifies the active session and returns user info.
"""
from fastapi import APIRouter, Depends
from ..auth import get_current_user as resolve_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def me(user: dict = Depends(resolve_current_user)):
    return {
        "ok": True,
        "user_id": user["id"],
        "email": user["email"],
        "name": user.get("name"),
        "message": "Authenticated via Better Auth",
    }
