from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from core.database_2 import get_session
from core.security import verify_password, create_access_token
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
    mail: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.mail == mail)).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": user.mail})

    response = RedirectResponse(
        url="/profil",
        status_code=303,
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )

    return response


# Logout
@router.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(
        key="access_token",
        path="/",
    )
    return response
