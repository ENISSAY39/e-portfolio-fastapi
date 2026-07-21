import hmac
import secrets

from fastapi import HTTPException, Request, status
from starlette.responses import Response

from core.config import settings


CSRF_COOKIE_NAME = "csrf_token"
CSRF_TOKEN_BYTES = 32
CSRF_MAX_AGE_SECONDS = 60 * 60 * 2


def get_or_create_csrf_token(request: Request) -> str:
    token = request.cookies.get(CSRF_COOKIE_NAME)
    if token and 32 <= len(token) <= 256:
        return token
    return secrets.token_urlsafe(CSRF_TOKEN_BYTES)


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=CSRF_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.cookie_secure_enabled,
        samesite="lax",
        path="/",
    )


def validate_csrf_token(request: Request, submitted_token: str) -> None:
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
