"""
Security module - Clerk JWT Authentication

Migrated from cookie-based sessions to stateless JWT auth.
All user data comes from Clerk - no local User table needed.
"""
from .clerk_auth import require_clerk_auth

# Re-export for backward compatibility with existing routes
require_auth = require_clerk_auth
