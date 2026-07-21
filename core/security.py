"""Provide password hashing and signed JWT access-token primitives."""

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from core.config import settings


# Encoding and decoding are restricted to the same explicit algorithm, avoiding
# acceptance of an attacker-selected JWT algorithm.
ALGORITHM = "HS256"

# ``recommended`` lets pwdlib select a modern password-hashing algorithm and
# encode its parameters alongside the resulting hash.
password_hash = PasswordHash.recommended()


def hash_password(password: str):
    """Return a one-way password hash suitable for persistent storage."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    """Verify a candidate password and treat malformed hashes as a mismatch."""
    try:
        return password_hash.verify(plain_password, hashed_password)
    except (TypeError, ValueError):
        # Authentication must fail closed if stored data cannot be parsed.
        return False


def create_access_token(data: dict):
    """Sign a copy of the supplied claims with issued-at and expiry timestamps."""
    # Copying prevents this helper from mutating the caller's claim dictionary.
    to_encode = data.copy()

    # Timezone-aware UTC values avoid local-time and daylight-saving ambiguity.
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": now})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def decode_access_token(token: str | None):
    """Decode and validate an access token, returning ``None`` on any failure."""
    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            # Every accepted access token must identify a subject and expire.
            options={"require": ["exp", "sub"]},
        )

        return payload

    except (jwt.InvalidTokenError, TypeError):
        # Callers receive one unauthenticated result without leaking why a token
        # failed signature, structure, or expiry validation.
        return None
