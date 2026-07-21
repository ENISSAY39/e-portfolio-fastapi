"""Implement double-submit-cookie CSRF protection for HTML forms."""

import hmac
import secrets

from fastapi import HTTPException, Request, status
from starlette.responses import Response

from core.config import settings


# CSRF tokens are independent from authentication tokens and intentionally use
# their own cookie name and shorter lifetime.
CSRF_COOKIE_NAME = "csrf_token"
CSRF_TOKEN_BYTES = 32
CSRF_MAX_AGE_SECONDS = 60 * 60 * 2


def get_or_create_csrf_token(request: Request) -> str:
    """Reuse a plausibly formed cookie token or create a cryptographic token."""
    token = request.cookies.get(CSRF_COOKIE_NAME)
    # The size bounds reject obviously malformed input while accepting the
    # URL-safe encoding length produced by ``token_urlsafe``.
    if token and 32 <= len(token) <= 256:
        return token
    return secrets.token_urlsafe(CSRF_TOKEN_BYTES)


def set_csrf_cookie(response: Response, token: str) -> None:
    """Attach the CSRF token cookie using environment-aware security flags."""
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=CSRF_MAX_AGE_SECONDS,
        # Templates receive the matching form value server-side, so browser
        # scripts never need to read this cookie.
        httponly=True,
        secure=settings.cookie_secure_enabled,
        # Lax blocks most cross-site form POSTs while preserving normal links.
        samesite="lax",
        path="/",
    )


def validate_csrf_token(request: Request, submitted_token: str) -> None:
    """Reject a form unless its token exactly matches the CSRF cookie.

    ``compare_digest`` avoids data-dependent comparison timing. Both values are
    required because accepting an absent pair would defeat CSRF protection.
    """
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if (
        not cookie_token
        or not submitted_token
        or not hmac.compare_digest(cookie_token, submitted_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired CSRF token",
        )
