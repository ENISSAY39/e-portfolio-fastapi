"""Unit tests for double-submit-cookie CSRF protection."""

import pytest
from fastapi import HTTPException, status
from starlette.requests import Request
from starlette.responses import Response

import core.csrf as csrf


def make_request(cookie_token: str | None = None) -> Request:
    """Build a minimal HTTP request with an optional CSRF cookie."""
    headers: list[tuple[bytes, bytes]] = []
    if cookie_token is not None:
        headers.append(
            (
                b"cookie",
                f"{csrf.CSRF_COOKIE_NAME}={cookie_token}".encode("ascii"),
            )
        )

    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/profil",
            "raw_path": b"/profil",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 443),
        }
    )


def test_get_or_create_csrf_token_reuses_a_well_formed_cookie() -> None:
    existing_token = "a" * 32

    assert csrf.get_or_create_csrf_token(make_request(existing_token)) == existing_token


@pytest.mark.parametrize("cookie_token", [None, "too-short", "x" * 257])
def test_get_or_create_csrf_token_replaces_missing_or_malformed_cookie(
    cookie_token: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(csrf.secrets, "token_urlsafe", lambda size: f"generated-{size}")

    assert csrf.get_or_create_csrf_token(make_request(cookie_token)) == "generated-32"


@pytest.mark.parametrize("secure", [False, True])
def test_set_csrf_cookie_uses_expected_security_attributes(
    secure: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(csrf.settings, "cookie_secure", secure)
    response = Response()

    csrf.set_csrf_cookie(response, "csrf-value")

    cookie_header = response.headers["set-cookie"]
    assert f"{csrf.CSRF_COOKIE_NAME}=csrf-value" in cookie_header
    assert f"Max-Age={csrf.CSRF_MAX_AGE_SECONDS}" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/" in cookie_header
    assert "SameSite=lax" in cookie_header
    assert ("Secure" in cookie_header) is secure


def test_validate_csrf_token_accepts_an_exact_cookie_match() -> None:
    token = "matching-csrf-token"

    assert csrf.validate_csrf_token(make_request(token), token) is None


@pytest.mark.parametrize(
    ("cookie_token", "submitted_token"),
    [
        (None, "submitted-token"),
        ("cookie-token", ""),
        ("cookie-token", "different-token"),
    ],
)
def test_validate_csrf_token_rejects_missing_or_mismatched_values(
    cookie_token: str | None,
    submitted_token: str,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        csrf.validate_csrf_token(make_request(cookie_token), submitted_token)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Invalid or expired CSRF token"
