import hashlib
import hmac
import secrets
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Prefix for all generated keys
API_KEY_PREFIX = "void_live_"


def generate_api_key() -> str:
    """Generate a high-entropy cryptographically secure API key."""
    return f"{API_KEY_PREFIX}{secrets.token_hex(24)}"


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256 for secure DB persistence."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Constant-time verification of an API key against its hash."""
    return hmac.compare_digest(hash_api_key(plain_key), hashed_key)


async def get_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> Optional[str]:
    """Dependency that extracts and validates presence of API key."""
    if not api_key:
        return None
    return api_key


async def require_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """Dependency enforcing that a valid API key must be supplied."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required 'X-API-Key' authentication header",
        )
    return api_key


# ---------------------------------------------------------------------------
# JWT & RBAC Authentication (Roles: ADMIN, OPERATOR, VIEWER)
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import settings

ROLE_HIERARCHY = {
    "ADMIN": 3,
    "OPERATOR": 2,
    "VIEWER": 1,
}


def create_access_token(
    payload: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Issue a cryptographically signed JWT access token with role claims."""
    to_encode = payload.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify signature and expiry of a JWT access token."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authorization token: {e}",
        )


def verify_rbac_role(user_role: str, minimum_required_role: str) -> bool:
    """Validate if user's role meets or exceeds the required privilege level."""
    user_level = ROLE_HIERARCHY.get(user_role.upper(), 0)
    required_level = ROLE_HIERARCHY.get(minimum_required_role.upper(), 999)
    return user_level >= required_level

