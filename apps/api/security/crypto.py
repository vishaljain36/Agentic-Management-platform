"""AES-256-GCM Envelope Encryption for User BYO LLM API Keys.

Implements Section 2.2 of Production Launch Blueprint:
  Ciphertext = AES-256-GCM(PlaintextKey, MasterKMSKey, IV)

Features:
- AES-256-GCM authenticated encryption (protects confidentiality and integrity)
- Cryptographic 12-byte (96-bit) Initialization Vector (IV) generated per encryption
- Authentication tag verification preventing ciphertext tampering
- Versioned envelope payload for zero-downtime KMS master key rotation
- Compact string and structured dictionary serialization
"""

import os
import base64
import hashlib
from typing import Optional, Dict, Any, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from app.core.config import settings

ENCRYPTION_VERSION = "v1"
IV_LENGTH_BYTES = 12  # Standard 96-bit IV for AES-GCM
KEY_LENGTH_BYTES = 32  # 256-bit key for AES-256


def derive_master_key(secret: Optional[str] = None) -> bytes:
    """Derive a deterministic 32-byte (256-bit) key from the KMS secret or JWT_SECRET."""
    raw = secret or os.getenv("KMS_MASTER_KEY") or os.getenv("MASTER_ENCRYPTION_KEY") or settings.JWT_SECRET
    # SHA-256 guarantees exact 32 bytes for AES-256
    return hashlib.sha256(raw.encode("utf-8")).digest()


def encrypt_api_key(
    plaintext_key: str,
    master_key: Optional[bytes] = None,
    associated_data: Optional[bytes] = None,
) -> Dict[str, str]:
    """Encrypt a plaintext API key with AES-256-GCM and a unique IV.
    
    Returns:
        dict: {
            "ciphertext": base64 string,
            "iv": base64 string,
            "version": "v1",
            "algorithm": "AES-256-GCM"
        }
    """
    key = master_key or derive_master_key()
    if len(key) != KEY_LENGTH_BYTES:
        raise ValueError(f"Master key must be exactly {KEY_LENGTH_BYTES} bytes for AES-256.")

    # Generate fresh cryptographic nonce (IV)
    iv = os.urandom(IV_LENGTH_BYTES)
    aesgcm = AESGCM(key)

    plaintext_bytes = plaintext_key.encode("utf-8")
    # AESGCM encrypt appends the 16-byte tag to the ciphertext
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext_bytes, associated_data)

    return {
        "ciphertext": base64.b64encode(ciphertext_with_tag).decode("utf-8"),
        "iv": base64.b64encode(iv).decode("utf-8"),
        "version": ENCRYPTION_VERSION,
        "algorithm": "AES-256-GCM",
    }


def encrypt_api_key_compact(
    plaintext_key: str,
    master_key: Optional[bytes] = None,
) -> str:
    """Encrypt and format as a compact string: v1:<b64_iv>:<b64_ciphertext_with_tag>."""
    envelope = encrypt_api_key(plaintext_key, master_key)
    return f"{envelope['version']}:{envelope['iv']}:{envelope['ciphertext']}"


def decrypt_api_key(
    envelope: Union[Dict[str, Any], str],
    master_key: Optional[bytes] = None,
    associated_data: Optional[bytes] = None,
) -> str:
    """Decrypt an AES-256-GCM envelope and verify the authentication tag.
    
    Raises ValueError if ciphertext is tampered with or tag verification fails.
    """
    key = master_key or derive_master_key()
    if len(key) != KEY_LENGTH_BYTES:
        raise ValueError(f"Master key must be exactly {KEY_LENGTH_BYTES} bytes for AES-256.")

    # Parse compact string format if passed as string
    if isinstance(envelope, str):
        parts = envelope.split(":")
        if len(parts) == 3:
            version, b64_iv, b64_ciphertext = parts
        else:
            raise ValueError("Malformed compact encrypted envelope string.")
    elif isinstance(envelope, dict):
        version = envelope.get("version", ENCRYPTION_VERSION)
        b64_iv = envelope.get("iv")
        b64_ciphertext = envelope.get("ciphertext")
        if not b64_iv or not b64_ciphertext:
            raise ValueError("Envelope dictionary missing 'iv' or 'ciphertext' keys.")
    else:
        raise TypeError("Envelope must be a dict or compact string.")

    try:
        iv = base64.b64decode(b64_iv)
        ciphertext_with_tag = base64.b64decode(b64_ciphertext)
    except Exception as e:
        raise ValueError(f"Invalid base64 encoding in encrypted envelope: {e}")

    aesgcm = AESGCM(key)
    try:
        decrypted_bytes = aesgcm.decrypt(iv, ciphertext_with_tag, associated_data)
        return decrypted_bytes.decode("utf-8")
    except InvalidTag:
        raise ValueError("Decryption failed: Ciphertext or IV authentication tag mismatch (tampering detected).")
    except Exception as e:
        raise ValueError(f"Decryption error: {e}")


def rotate_api_key(
    envelope: Union[Dict[str, Any], str],
    old_master_key: bytes,
    new_master_key: bytes,
) -> Union[Dict[str, str], str]:
    """Re-encrypt payload under a new KMS master key during scheduled key rotation."""
    plaintext = decrypt_api_key(envelope, master_key=old_master_key)
    if isinstance(envelope, str):
        return encrypt_api_key_compact(plaintext, master_key=new_master_key)
    return encrypt_api_key(plaintext, master_key=new_master_key)

