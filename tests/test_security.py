"""Unit tests for password hashing and JWT primitives."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from core.config import settings
from core.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip_and_wrong_password_rejection() -> None:
    password = "CorrectHorse9"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password) is True
    assert verify_password("WrongPassword9", hashed_password) is False


@pytest.mark.parametrize("malformed_hash", ["", "not-a-password-hash", None])
def test_verify_password_fails_closed_for_malformed_hashes(
    malformed_hash: str | None,
) -> None:
    assert verify_password("CorrectHorse9", malformed_hash) is False  # type: ignore[arg-type]


def test_access_token_round_trip_preserves_claims_and_adds_timestamps() -> None:
    claims = {"sub": "ada@example.com", "role": "user"}
    original_claims = claims.copy()

    token = create_access_token(claims)
    payload = decode_access_token(token)

    assert claims == original_claims
    assert payload is not None
    assert payload["sub"] == "ada@example.com"
    assert payload["role"] == "user"
    assert payload["exp"] - payload["iat"] == settings.access_token_expire_minutes * 60


@pytest.mark.parametrize("token", [None, "", "not-a-jwt"])
def test_decode_access_token_rejects_missing_or_malformed_tokens(
    token: str | None,
) -> None:
    assert decode_access_token(token) is None


def test_decode_access_token_rejects_a_token_signed_with_another_secret() -> None:
    token = jwt.encode(
        {
            "sub": "ada@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        f"{settings.secret_key}-different",
        algorithm=ALGORITHM,
    )

    assert decode_access_token(token) is None


def test_decode_access_token_rejects_an_expired_token() -> None:
    token = jwt.encode(
        {
            "sub": "ada@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    assert decode_access_token(token) is None


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        {"sub": "ada@example.com"},
    ],
)
def test_decode_access_token_requires_subject_and_expiry(claims: dict) -> None:
    token = jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)

    assert decode_access_token(token) is None


def test_decode_access_token_rejects_an_unapproved_algorithm() -> None:
    token = jwt.encode(
        {
            "sub": "ada@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.secret_key,
        algorithm="HS384",
    )

    assert decode_access_token(token) is None
