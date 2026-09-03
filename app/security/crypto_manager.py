"""
crypto_manager.py

AES-256-GCM application-layer payload encryption, compatible with the
companion Java implementation in java_client/CryptoManager.java.

Wire format (all bytes, then base64url-encoded as a single string):

    [ 12-byte nonce ][ ciphertext ][ 16-byte GCM auth tag ]

This matches the standard output layout of Java's
Cipher.getInstance("AES/GCM/NoPadding") (ciphertext + 16-byte tag
concatenated) prefixed with the nonce we generate ourselves, and it
matches PyCryptodome / `cryptography`'s AESGCM, which also appends the
tag to the ciphertext.

Security notes:
- Uses a fresh random 12-byte nonce for every encryption call, as
  required for AES-GCM.
- Uses the standard 16-byte (128-bit) authentication tag.
- Never re-uses a nonce with the same key.
- The key itself is NOT generated or stored here - it's provided by
  app.config.get_settings().PAYLOAD_ENCRYPTION_KEY (see config.py and
  the README section on key management / session credentials).
"""
import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

NONCE_SIZE = 12  # bytes, standard for GCM
TAG_SIZE = 16    # bytes, standard GCM tag length


class DecryptionError(Exception):
    """Raised when a payload cannot be decrypted or its integrity check fails."""
    pass


def _derive_key(raw_key: str) -> bytes:
    """
    Normalizes an arbitrary-length secret string into exactly 32 bytes
    (AES-256) using SHA-256. This lets the operator supply any
    reasonably strong secret (e.g. a token_urlsafe(32) string) via the
    PAYLOAD_ENCRYPTION_KEY env var without worrying about exact byte
    length. The Java side must perform the identical derivation
    (SHA-256 of the UTF-8 key string) to stay compatible.
    """
    return hashlib.sha256(raw_key.encode("utf-8")).digest()


def encrypt_data(data: str, key: str) -> str:
    """
    Encrypts a UTF-8 string and returns a base64url (no padding) string
    containing nonce || ciphertext || tag.
    """
    aes_key = _derive_key(key)
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(aes_key)
    ciphertext_and_tag = aesgcm.encrypt(nonce, data.encode("utf-8"), None)
    blob = nonce + ciphertext_and_tag
    return base64.urlsafe_b64encode(blob).decode("ascii").rstrip("=")


def decrypt_data(encrypted_data: str, key: str) -> str:
    """
    Reverses encrypt_data(). Raises DecryptionError if the payload is
    malformed or the authentication tag does not verify (i.e. the data
    was tampered with, corrupted, or encrypted with a different key).
    """
    aes_key = _derive_key(key)
    try:
        padded = encrypted_data + "=" * (-len(encrypted_data) % 4)
        blob = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception as exc:
        raise DecryptionError(f"Malformed base64 payload: {exc}") from exc

    if len(blob) < NONCE_SIZE + TAG_SIZE:
        raise DecryptionError("Payload too short to contain nonce + tag")

    nonce = blob[:NONCE_SIZE]
    ciphertext_and_tag = blob[NONCE_SIZE:]

    aesgcm = AESGCM(aes_key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext_and_tag, None)
    except InvalidTag as exc:
        raise DecryptionError("Authentication tag verification failed") from exc
    except Exception as exc:
        raise DecryptionError(f"Decryption failed: {exc}") from exc

    return plaintext.decode("utf-8")
