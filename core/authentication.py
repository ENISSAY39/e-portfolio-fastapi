"""Resolve the currently authenticated user from the access-token cookie."""

from fastapi import Request
from sqlmodel import Session, select

from core.security import decode_access_token
from schemas.User import User


def get_authenticated_user(request: Request, session: Session) -> User | None:
    """Return the user named by a valid JWT, or ``None`` when unauthenticated.

    Token decoding handles missing, malformed, expired, or invalid signatures.
    The database lookup is still required because a valid token may reference a
    user that has since been removed.
    """
    payload = decode_access_token(request.cookies.get("access_token"))
    if not payload:
        return None

    mail = payload.get("sub")
    # Never pass an attacker-controlled non-string subject into the SQL query.
    if not isinstance(mail, str):
        return None
    return session.exec(select(User).where(User.mail == mail)).first()
