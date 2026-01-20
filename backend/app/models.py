"""
Database Models

User model removed - Clerk is now the source of truth for user data.
Keep this file for future non-auth models if needed.
"""
from .database import Base

# User model removed - authentication handled by Clerk
# All user data isolation uses Clerk user_id from JWT
