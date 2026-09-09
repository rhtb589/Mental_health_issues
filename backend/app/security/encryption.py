"""Field-level encryption for sensitive health data.

Requirement (Privacy):
  "All screening answers and scores are treated as sensitive health data."

This module provides envelope-style symmetric encryption (Fernet / AES-128-CBC
in CBC mode with HMAC) so that answers and scores at rest cannot be read without
the key. In production the key should be sourced from a KMS / secrets manager
rather than an environment variable.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class FieldEncryptor:
    """Encrypts/decrypts individual fields and JSON payloads.

    Values are serialised to JSON before encryption so that structured sensitive
    payloads (e.g. a list of responses) can be stored as an opaque blob.
    """

    def __init__(self, key: str | None = None) -> None:
        raw = (key or settings.field_encryption_key).encode()
        # Allow raw 32-byte keys as well as url-safe base64 Fernet keys.
        try:
            self._fernet = Fernet(raw if _is_fernet_key(raw) else base64.urlsafe_b64encode(raw[:32].ljust(32, b"0")))
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError("Invalid field_encryption_key") from exc

    def encrypt(self, value: Any) -> str:
        payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
        return self._fernet.encrypt(payload).decode()

    def decrypt(self, token: str) -> Any:
        try:
            plaintext = self._fernet.decrypt(token.encode())
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt sensitive field") from exc
        return json.loads(plaintext)

    def encrypt_raw(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt_raw(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()


def _is_fernet_key(raw: bytes) -> bool:
    try:
        Fernet(raw)
        return True
    except Exception:
        return False


# Module-level singleton for convenience.
def _create_encryptor() -> FieldEncryptor:
    """Create the global encryptor, validating the key is not a placeholder."""
    raw = settings.field_encryption_key.encode()
    if not _is_fernet_key(raw) and settings.field_encryption_key in (
        "CHANGE_ME_ENCRYPTION_KEY",
        "replace-with-fernet-key",
    ):
        raise SystemExit(
            "MHC_FIELD_ENCRYPTION_KEY is a placeholder. "
            "Generate a real key: cd backend && python -c "
            "\"from app.security.encryption import generate_key; print(generate_key())\""
        )
    return FieldEncryptor()


encryptor = _create_encryptor()


def generate_key() -> str:
    """Helper to generate a new Fernet key (used by ops, not at runtime)."""
    return Fernet.generate_key().decode()


def random_subject_token() -> str:
    """Pseudonymous token used for de-identified storage."""
    return base64.urlsafe_b64encode(os.urandom(18)).decode()
