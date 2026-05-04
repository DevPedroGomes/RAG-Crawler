"""
Better Auth bridge for FastAPI.

Better Auth (managed by the Next.js frontend) writes session rows into the
shared Postgres database. This module reads the session cookie from the
incoming request and resolves it to a user via SQL on the
``"session"`` and ``"user"`` tables.

Cookies (set by Better Auth):
- ``__Secure-better-auth.session_token`` — production (HTTPS)
- ``better-auth.session_token``         — local / non-HTTPS

Format: ``<token>.<signature>``. Better Auth uses the unsigned token as the
session row key. We accept either form (signed or unsigned) and use the
portion before the first dot for the SQL lookup, since older clients may
send the raw token.

This is a read-only path; nothing on the Python side ever creates or
mutates Better Auth sessions.
"""
from __future__ import annotations

import logging
import time
import threading
from typing import Optional

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from fastapi import HTTPException, Request

from .config import settings


logger = logging.getLogger(__name__)


SESSION_COOKIE_NAMES = (
    "__Secure-better-auth.session_token",
    "better-auth.session_token",
)


_pool: Optional[ThreadedConnectionPool] = None
_pool_lock = threading.Lock()


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is None:
            # The shared Postgres URL — Better Auth created the tables.
            # Use a small dedicated pool here so this never starves the
            # SQLAlchemy pool used by the rest of the app.
            _pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=4,
                dsn=settings.DATABASE_URL,
            )
    return _pool


def _extract_session_token(request: Request) -> Optional[str]:
    for name in SESSION_COOKIE_NAMES:
        raw = request.cookies.get(name)
        if not raw:
            continue
        # Cookie value is "<token>.<signature>" — Better Auth stores `<token>`.
        token = raw.split(".", 1)[0]
        if token:
            return token
    return None


def _query_user_for_token(token: str) -> Optional[dict]:
    """Returns {id, email, name} or None if token is invalid/expired."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT u.id, u.email, u.name
                FROM "session" s
                JOIN "user" u ON u.id = s."userId"
                WHERE s.token = %s AND s."expiresAt" > NOW()
                LIMIT 1
                ''',
                (token,),
            )
            row = cur.fetchone()
            conn.commit()  # release any txn snapshot
            if not row:
                return None
            return {"id": row[0], "email": row[1], "name": row[2]}
    except psycopg2.Error as e:
        logger.warning("better-auth session lookup failed: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        pool.putconn(conn)


def get_current_user(request: Request) -> dict:
    """FastAPI dependency for protected routes.

    Returns:
        dict with keys: ``id``, ``email``, ``name``.

    Raises:
        HTTPException 401 if no valid session.
    """
    token = _extract_session_token(request)
    if not token:
        raise HTTPException(401, "Authentication required")

    user = _query_user_for_token(token)
    if not user:
        raise HTTPException(401, "Invalid or expired session")

    # Track activity for showcase auto-cleanup.
    try:
        from .user_activity import update_user_activity
        update_user_activity(user["id"])
    except Exception:
        pass

    return user


def require_auth_user_id(request: Request) -> str:
    """Convenience wrapper returning just the user id (most routes only need this)."""
    return get_current_user(request)["id"]


def get_user_id_for_rate_limit(request: Request) -> str:
    """Rate-limit key derived from the session — never falls back to IP, so
    unauthenticated traffic is rejected at auth and Traefik's global limiter
    handles abuse.
    """
    try:
        return f"user:{require_auth_user_id(request)}"
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required")


