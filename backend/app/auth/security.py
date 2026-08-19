"""Password hashing and JWT encoding.

Pure cryptography and token plumbing: nothing here knows about tickets,
workflows or the domain adapter.
"""

import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import settings


def _build_password_hash() -> PasswordHash:
    """Argon2 when the extra is installed, bcrypt otherwise."""
    try:
        from pwdlib.hashers.argon2 import Argon2Hasher

        return PasswordHash((Argon2Hasher(),))
    except ImportError:  # pragma: no cover - depends on the installed extras
        from pwdlib.hashers.bcrypt import BcryptHasher

        return PasswordHash((BcryptHasher(),))


_password_hash = _build_password_hash()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """False rather than an exception for accounts that cannot log in."""
    if not password_hash:
        return False

    try:
        return _password_hash.verify(password, password_hash)
    except Exception:
        return False


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(32))


def burn_password_check(password: str) -> None:
    """Verify against a throwaway hash.

    Called when the email does not exist, so that a missing account does not
    answer measurably faster than a wrong password.
    """
    verify_password(password, _dummy_hash())


def create_access_token(
    *,
    user_id: UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Sign a token identifying the user.

    The `role` claim is informational (the frontend uses it to lay out the UI).
    Authorization always re-reads the role from the database, so a stale claim
    can never widen someone's permissions.
    """
    expires_in = expires_delta or timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    now = datetime.now(UTC)

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + expires_in,
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raise `jwt.PyJWTError` if the token is malformed, forged or expired."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
