"""Test Case BE-UT-06: Cryptographic BYO-Key Vault (AES-256-GCM Encryption/Decryption at Rest).

Specification:
1. Pass raw provider key 'sk-proj-live-1234567890abcdef' to encrypt_api_key().
2. Inspect returned ciphertext string and IV nonce.
3. Confirm plain text key is nowhere visible in raw ciphertext or compact string.
4. Pass ciphertext to decrypt_api_key() and verify exact match to original key.
5. Confirm raw API keys are never written in plain text.
6. Verify wrong master key or tampered ciphertext throws DecryptionError.
"""

import os
import pytest
from security.crypto import (
    encrypt_api_key,
    decrypt_api_key,
    encrypt_api_key_compact,
    derive_master_key,
    DecryptionError,
)


def test_be_ut_06_aes_256_gcm_envelope_encryption_cycle():
    """Encrypt and decrypt raw LLM API key with randomized IV and 256-bit master key."""
    raw_key = "sk-proj-live-1234567890abcdef"
    master_key = derive_master_key("test-production-kms-master-secret-key-32")

    # 1. Encrypt key
    envelope = encrypt_api_key(raw_key, master_key=master_key)

    # 2. Inspect ciphertext and IV
    assert "ciphertext" in envelope
    assert "iv" in envelope
    assert envelope["algorithm"] == "AES-256-GCM"
    assert envelope["version"] == "v1"

    # 3. Plaintext key must NOT be visible anywhere in ciphertext or IV
    assert raw_key not in envelope["ciphertext"]
    assert raw_key not in envelope["iv"]

    # 4. Decrypt key and verify exact restoration
    decrypted = decrypt_api_key(envelope, master_key=master_key)
    assert decrypted == raw_key


def test_be_ut_06_compact_string_serialization_and_randomized_iv():
    """Two encryptions of the identical key produce distinct ciphertexts due to fresh IV generation."""
    raw_key = "sk-proj-live-1234567890abcdef"
    master_key = derive_master_key("another-secret-seed-key-value-999")

    compact_1 = encrypt_api_key_compact(raw_key, master_key=master_key)
    compact_2 = encrypt_api_key_compact(raw_key, master_key=master_key)

    # Both must be formatted as v1:<iv>:<ciphertext>
    assert compact_1.startswith("v1:")
    assert compact_2.startswith("v1:")

    # Because each encryption uses an os.urandom(12) IV, compact representations must differ
    assert compact_1 != compact_2

    # Both decrypt back to the identical plaintext
    assert decrypt_api_key(compact_1, master_key=master_key) == raw_key
    assert decrypt_api_key(compact_2, master_key=master_key) == raw_key


def test_be_ut_06_wrong_master_key_throws_decryption_error():
    """Attempting decryption with an invalid master key throws DecryptionError."""
    raw_key = "sk-proj-live-1234567890abcdef"
    valid_key = derive_master_key("correct-master-key-seed-alpha")
    wrong_key = derive_master_key("incorrect-attacker-key-seed-beta")

    envelope = encrypt_api_key(raw_key, master_key=valid_key)

    with pytest.raises(DecryptionError) as exc_info:
        decrypt_api_key(envelope, master_key=wrong_key)

    assert "Decryption failed" in str(exc_info.value) or "Decryption error" in str(exc_info.value)


def test_be_ut_06_tampered_ciphertext_throws_decryption_error():
    """Tampering with a single byte of ciphertext or IV causes authentication tag verification to fail."""
    raw_key = "sk-proj-live-1234567890abcdef"
    master_key = derive_master_key()

    envelope = encrypt_api_key(raw_key, master_key=master_key)

    # Flip characters in ciphertext
    tampered_ciphertext = "A" + envelope["ciphertext"][1:]
    tampered_envelope = {**envelope, "ciphertext": tampered_ciphertext}

    with pytest.raises(DecryptionError):
        decrypt_api_key(tampered_envelope, master_key=master_key)

