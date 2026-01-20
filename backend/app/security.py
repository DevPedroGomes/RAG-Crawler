"""
Security module - Clerk JWT Authentication

Migrated from cookie-based sessions to stateless JWT auth.
All user data comes from Clerk - no local User table needed.
"""
from fastapi import Request
from .clerk_auth import require_clerk_auth

# Re-export for backward compatibility with existing routes
require_auth = require_clerk_auth


def validate_csrf(request: Request):
    """DEPRECATED: CSRF not needed with stateless JWT auth"""
    pass


def validate_session(request: Request) -> str:
    """DEPRECATED: Use require_clerk_auth instead"""
    raise NotImplementedError("Use require_clerk_auth dependency")
