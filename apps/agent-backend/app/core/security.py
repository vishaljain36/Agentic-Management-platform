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
