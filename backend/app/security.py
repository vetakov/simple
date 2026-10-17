"""Small password and session-token helpers used by the API."""

from __future__ import annotations

import hashlib
import hmac
import secrets


PASSWORD_ITERATIONS = 310_000


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_value.encode("ascii"),
        PASSWORD_ITERATIONS,
    )
    return digest.hex(), salt_value


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt=salt)
    return hmac.compare_digest(candidate, password_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def session_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

