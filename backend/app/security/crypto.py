"""Cryptographic primitives: password hashing, SHA-256 digests, field encryption.

Field encryption (Phase 5): authenticated encryption with AES-256-GCM from the
`cryptography` library. The 256-bit key is derived with SHA-256 over the configured
field key, each value gets a fresh 96-bit nonce, and the GCM tag authenticates the
ciphertext, so a modified value fails to decrypt instead of silently decrypting to
garbage. Values written by the earlier development profile ("enc:v1:" HMAC
keystream) are still readable so existing records keep working, but nothing new is
written in that format.

The public interface is unchanged: encrypt_field(str) -> str, decrypt_field(str) -> str.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..config import FIELD_ENCRYPTION_KEY

PBKDF2_ROUNDS = 120_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


# ---------------------------------------------------------------------------
# AES-256-GCM field encryption (current profile)
# ---------------------------------------------------------------------------
_AAD = b"crimenet-field-encryption-v2"


def _field_key() -> bytes:
    """256-bit key derived from the configured field-encryption key."""
    return hashlib.sha256(FIELD_ENCRYPTION_KEY.encode("utf-8")).digest()


def encrypt_field(plaintext: str) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(_field_key()).encrypt(nonce, plaintext.encode("utf-8"), _AAD)
    return "enc:v2:" + urlsafe_b64encode(nonce + ct).decode()


def decrypt_field(token: str) -> str:
    if token.startswith("enc:v2:"):
        try:
            raw = urlsafe_b64decode(token[len("enc:v2:"):].encode())
            return AESGCM(_field_key()).decrypt(raw[:12], raw[12:], _AAD).decode("utf-8")
        except InvalidTag as exc:
            raise ValueError("Encrypted field failed integrity verification "
                             "(AES-GCM authentication tag mismatch)") from exc
        except Exception as exc:  # malformed envelope
            raise ValueError(f"Encrypted field could not be decoded: {exc}") from exc
    if token.startswith("enc:v1:"):
        return _decrypt_legacy_v1(token)
    return token


# ---------------------------------------------------------------------------
# Legacy development profile - read-only, so previously stored values still open
# ---------------------------------------------------------------------------
def _keystream(nonce: bytes, length: int) -> bytes:
    """HMAC-SHA256 counter-mode keystream (development field-encryption profile).

    Production deployments must replace this with an AES-GCM envelope backed by a
    managed KMS. The interface (encrypt_field / decrypt_field) stays identical.
    """
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hmac.new(FIELD_ENCRYPTION_KEY.encode(), nonce + counter.to_bytes(4, "big"),
                        hashlib.sha256).digest()
        counter += 1
    return bytes(out[:length])


def _decrypt_legacy_v1(token: str) -> str:
    raw = urlsafe_b64decode(token[len("enc:v1:"):].encode())
    nonce, tag, ct = raw[:12], raw[12:28], raw[28:]
    expected = hmac.new(FIELD_ENCRYPTION_KEY.encode(), nonce + ct, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expected):
        raise ValueError("Encrypted field failed integrity verification")
    return bytes(a ^ b for a, b in zip(ct, _keystream(nonce, len(ct)))).decode("utf-8")


def mask(value: str, keep: int = 4) -> str:
    if len(value) <= keep:
        return "*" * len(value)
    return "*" * (len(value) - keep) + value[-keep:]
