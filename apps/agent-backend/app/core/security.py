import hashlib
import hmac
from typing import Optional


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256 for secure DB persistence."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Constant-time verification of an API key against its hash."""
    return hmac.compare_digest(hash_api_key(plain_key), hashed_key)

