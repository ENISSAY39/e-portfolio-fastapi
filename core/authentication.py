from fastapi import Request
from sqlmodel import Session, select

from core.security import decode_access_token
from schemas.User import User


def get_authenticated_user(request: Request, session: Session) -> User | None:
    payload = decode_access_token(request.cookies.get("access_token"))
    if not payload:
        return None

    mail = payload.get("sub")
    if not isinstance(mail, str):
        return None
    return session.exec(select(User).where(User.mail == mail)).first()
