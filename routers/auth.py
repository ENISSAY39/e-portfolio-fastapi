from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from core.config import settings
from core.csrf import CSRF_COOKIE_NAME, validate_csrf_token
from core.database import get_session
from core.security import verify_password, create_access_token
from core.validation import normalize_email
from schemas.User import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# home page


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    page: int = 1,
    session: Session = Depends(get_session),
):
    items_per_page = 10

    # Ensure page is at least 1
    if page < 1:
        page = 1

    # Get total count of users
    total_users = len(session.exec(select(User)).all())
    total_pages = (total_users + items_per_page - 1) // items_per_page

    # Ensure page doesn't exceed total pages
    if page > total_pages and total_pages > 0:
        page = total_pages

    # Calculate offset
    offset = (page - 1) * items_per_page

    # Get users for current page
    users = session.exec(select(User).offset(offset).limit(items_per_page)).all()

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "request": request,
            "users": users,
            "current_page": page,
            "total_pages": total_pages,
            "has_previous": page > 1,
            "has_next": page < total_pages,
            "previous_page": page - 1,
            "next_page": page + 1,
        },
    )


# search


@router.get("/search", response_class=HTMLResponse)
def search_users(
    request: Request,
    query: str = "",
    page: int = 1,
    session: Session = Depends(get_session),
):
    items_per_page = 10

    # Ensure page is at least 1
    if page < 1:
        page = 1

    # Get total count of search results
    total_users = len(session.exec(select(User).where(User.name.contains(query))).all())
    total_pages = (
        (total_users + items_per_page - 1) // items_per_page if total_users > 0 else 1
    )

    # Ensure page doesn't exceed total pages
    if page > total_pages and total_pages > 0:
        page = total_pages

    # Calculate offset
    offset = (page - 1) * items_per_page

    # Get users for current page
    users = session.exec(
        select(User)
        .where(User.name.contains(query))
        .offset(offset)
        .limit(items_per_page)
    ).all()

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "request": request,
            "users": users,
            "query": query,
            "current_page": page,
            "total_pages": total_pages,
            "has_previous": page > 1,
            "has_next": page < total_pages,
            "previous_page": page - 1,
            "next_page": page + 1,
        },
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
    request: Request,
    csrf_token: str = Form(""),
    mail: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    validate_csrf_token(request, csrf_token)

    try:
        normalized_mail = normalize_email(mail)
    except ValueError:
        normalized_mail = mail.strip().lower()

    user = session.exec(select(User).where(User.mail == normalized_mail)).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Invalid email or password.",
                "mail": normalized_mail,
            },
            status_code=401,
        )

    token = create_access_token(data={"sub": user.mail})

    response = RedirectResponse(
        url="/profil",
        status_code=303,
    )

    response.set_cookie(
        key="access_token",
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure_enabled,
        path="/",
    )

    return response


# Logout
@router.post("/logout")
def logout(request: Request, csrf_token: str = Form("")):
    validate_csrf_token(request, csrf_token)
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=settings.cookie_secure_enabled,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        secure=settings.cookie_secure_enabled,
        httponly=True,
        samesite="lax",
    )
    return response
