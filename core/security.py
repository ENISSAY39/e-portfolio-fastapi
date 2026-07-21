from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from core.config import settings


ALGORITHM = "HS256"


password_hash = PasswordHash.recommended()


# Hash password
def hash_password(password: str):
    return password_hash.hash(password)


# Verify password
def verify_password(plain_password: str, hashed_password: str):
    try:
        return password_hash.verify(plain_password, hashed_password)
    except (TypeError, ValueError):
        return False


# Create JWT token
def create_access_token(data: dict):
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": now})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


# Decode JWT token
def decode_access_token(token: str | None):
    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )

        return payload

    except (jwt.InvalidTokenError, TypeError):
        return None
