from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from core.database_2 import get_session
from core.security import verify_password, create_access_token
from schemas.User import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# Login page
@router.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request},
    )


@router.get("/login", response_class=HTMLResponse)
def login_page_alias(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request},
    )


# Login
@router.post("/login")
def login_user(
    mail: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(User.mail == mail)
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={
            "sub": user.mail
        }
    )

    response = RedirectResponse(
        url="/profil",
        status_code=303,
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
    )

    return response


# Logout
@router.get("/logout")
def logout():
    response = RedirectResponse(
        url="/",
        status_code=303,
    )

    response.delete_cookie("access_token")

    return response