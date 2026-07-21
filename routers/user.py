from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from datetime import date

from core.authentication import get_authenticated_user
from core.csrf import validate_csrf_token
from core.database import get_session
from core.security import hash_password
from core.validation import (
    clean_text,
    normalize_email,
    normalize_phone,
    parse_birth_date,
    validate_password,
)

from schemas.User import User
from schemas.Experiences import Experience
from schemas.Education import Education

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def calculate_age(birth_date: date) -> int:
    """Calcule l'âge à partir de la date de naissance"""
    today_date = date.today()
    age = today_date.year - birth_date.year
    # Soustraire 1 si l'anniversaire n'est pas encore passé cette année
    if (today_date.month, today_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


# profil public d'un utilisateur (affiché à tous les utilisateurs, même non connectés)
@router.get("/portfolio/{user_id}", response_class=HTMLResponse)
def public_portfolio(
    request: Request,
    user_id: int,
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)

    if not user:
        return RedirectResponse("/login", status_code=303)

    experiences = session.exec(
        select(Experience).where(Experience.user_id == user.id)
    ).all()

    educations = session.exec(
        select(Education).where(Education.user_id == user.id)
    ).all()

    return templates.TemplateResponse(
        request,
        "public_profile.html",
        {
            "request": request,
            "user": user,
            "experiences": experiences,
            "educations": educations,
        },
    )


# Form create user
@router.get("/create_user", response_class=HTMLResponse)
def show_form(request: Request):
    return templates.TemplateResponse(
        request,
        "create_user.html",
        {"request": request, "form_data": {}},
    )


# Create user
@router.post("/create_user")
def create_user(
    request: Request,
    csrf_token: str = Form(""),
    name: str = Form(...),
    first_name: str = Form(...),
    birth_date: str = Form(...),
    mail: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    validate_csrf_token(request, csrf_token)
    form_data = {
        "name": name,
        "first_name": first_name,
        "birth_date": birth_date,
        "mail": mail,
        "phone": phone,
    }

    try:
        cleaned_name = clean_text(name, "Name", 100)
        cleaned_first_name = clean_text(first_name, "First name", 100)
        birth_date_obj = parse_birth_date(birth_date)
        normalized_mail = normalize_email(mail)
        normalized_phone = normalize_phone(phone)
        validated_password = validate_password(password)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "create_user.html",
            {"request": request, "error": str(exc), "form_data": form_data},
            status_code=400,
        )

    existing_user = session.exec(
        select(User).where(User.mail == normalized_mail)
    ).first()
    if existing_user:
        return templates.TemplateResponse(
            request,
            "create_user.html",
            {
                "request": request,
                "error": "An account already exists with this email address.",
                "form_data": form_data,
            },
            status_code=409,
        )

    user = User(
        name=cleaned_name,
        first_name=cleaned_first_name,
        birth_date=birth_date_obj,
        mail=normalized_mail,
        phone=normalized_phone,
        hashed_password=hash_password(validated_password),
    )

    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return templates.TemplateResponse(
            request,
            "create_user.html",
            {
                "request": request,
                "error": "An account already exists with this email address.",
                "form_data": form_data,
            },
            status_code=409,
        )

    return RedirectResponse("/login", status_code=303)


# Profil
@router.get("/profil", response_class=HTMLResponse)
def show_profile(
    request: Request,
    session: Session = Depends(get_session),
):

    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Get experiences
    experiences = session.exec(
        select(Experience).where(Experience.user_id == user.id)
    ).all()

    # Get educations
    educations = session.exec(
        select(Education).where(Education.user_id == user.id)
    ).all()

    response = templates.TemplateResponse(
        request,
        "profil.html",
        {
            "request": request,
            "name": user.name,
            "first_name": user.first_name,
            "age": calculate_age(user.birth_date),
            "mail": user.mail,
            "phone": user.phone,
            "experiences": experiences,
            "educations": educations,
        },
    )

    # Prevent browser cache after logout
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response
