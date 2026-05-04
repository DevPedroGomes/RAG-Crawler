"""
Security module — Better Auth bridge.

Re-exports the auth dependency under the legacy ``require_auth`` name so
existing routes don't need to change.
"""
from .auth import require_auth_user_id

# Existing routes call ``Depends(require_auth)`` and expect a string user_id.
require_auth = require_auth_user_id
