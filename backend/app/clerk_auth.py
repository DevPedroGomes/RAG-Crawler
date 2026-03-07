"""
Clerk JWT Authentication for FastAPI

Verifies Clerk-issued JWTs using JWKS (JSON Web Key Set).
Extracts user_id from the 'sub' claim.
Validates 'azp' (authorized party) to ensure token is for this application.
"""
import logging
import time
import threading
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException
from .config import settings

logger = logging.getLogger(__name__)

_jwks_client: PyJWKClient | None = None
_jwks_client_created_at: float = 0
_jwks_lock = threading.Lock()
_JWKS_TTL_SECONDS = 300  # Refresh JWKS client every 5 minutes


def get_jwks_client() -> PyJWKClient:
    """
    Returns JWKS client for Clerk with TTL-based refresh.
    Recreates the client every 5 minutes to pick up key rotations.
    """
    global _jwks_client, _jwks_client_created_at

    now = time.monotonic()
    if _jwks_client and (now - _jwks_client_created_at) < _JWKS_TTL_SECONDS:
        return _jwks_client

    with _jwks_lock:
        # Double-check after acquiring lock
        if _jwks_client and (time.monotonic() - _jwks_client_created_at) < _JWKS_TTL_SECONDS:
            return _jwks_client

        jwks_url = settings.CLERK_JWKS_URL or "https://api.clerk.com/v1/jwks"
        _jwks_client = PyJWKClient(jwks_url)
        _jwks_client_created_at = time.monotonic()
        logger.debug("JWKS client refreshed")
        return _jwks_client


def verify_clerk_token(token: str) -> dict:
    """
    Verify Clerk JWT and return decoded payload.

    Args:
        token: JWT from Authorization header (without 'Bearer ' prefix)

    Returns:
        Decoded JWT payload with 'sub' (user_id), etc.

    Raises:
        HTTPException 401 if token is invalid
    """
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and verify signature
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,  # Clerk doesn't use standard aud
                "verify_iss": False,  # We validate azp instead
            }
        )

        # Validate azp (authorized party) if configured
        # This ensures the token was issued for YOUR application
        if settings.CLERK_AUTHORIZED_PARTIES:
            azp = payload.get("azp")
            allowed_parties = [p.strip() for p in settings.CLERK_AUTHORIZED_PARTIES.split(",")]

            if azp not in allowed_parties:
                logger.warning(f"Token azp '{azp}' not in allowed parties")
                raise HTTPException(401, "Token not authorized for this application")

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(401, "Invalid token")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(401, "Authentication failed")


def get_token_from_header(request: Request) -> str:
    """
    Extract Bearer token from Authorization header.

    Args:
        request: FastAPI Request

    Returns:
        JWT token string

    Raises:
        HTTPException 401 if header missing or malformed
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(401, "Authorization header required")

    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Invalid Authorization header format. Use: Bearer <token>")

    return parts[1]


def require_clerk_auth(request: Request) -> str:
    """
    FastAPI dependency for protected routes.

    Returns:
        user_id (Clerk user ID from 'sub' claim)

    Raises:
        HTTPException 401 if not authenticated
    """
    token = get_token_from_header(request)
    payload = verify_clerk_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token: missing user ID")

    # Track user activity for automatic cleanup (showcase mode)
    from .user_activity import update_user_activity
    update_user_activity(user_id)

    return user_id
