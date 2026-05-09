from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import date

from core.database_2 import get_session
from core.security import hash_password, decode_access_token

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


# Form create user
@router.get("/create_user", response_class=HTMLResponse)
def show_form(request: Request):
    return templates.TemplateResponse(
        request,
        "create_user.html",
        {"request": request},
    )


# Create user
@router.post("/create_user")
def create_user(
    name: str = Form(...),
    first_name: str = Form(...),
    birth_date: str = Form(...),
    mail: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    birth_date_obj = date.fromisoformat(birth_date)

    user = User(
        name=name,
        first_name=first_name,
        birth_date=birth_date_obj,
        mail=mail,
        phone=phone,
        hashed_password=hash_password(password),
    )

    print("DEBUG USER CREATED:", user)
    session.add(user)
    session.commit()
    session.refresh(user)

    return RedirectResponse("/", status_code=303)


# Profil
@router.get("/profil", response_class=HTMLResponse)
def show_profile(
    request: Request,
    session: Session = Depends(get_session),
):

    # Get JWT token from cookies
    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse("/", status_code=303)

    # Decode token
    payload = decode_access_token(token)

    if not payload:
        return RedirectResponse("/", status_code=303)

    # Get mail from token
    mail = payload.get("sub")

    if not mail:
        return RedirectResponse("/", status_code=303)

    # Get user
    user = session.exec(
        select(User).where(User.mail == mail)
    ).first()

    if not user:
        return RedirectResponse("/", status_code=303)

    # Get experiences
    experiences = session.exec(
        select(Experience).where(Experience.user_id == user.id)
    ).all()

    # Get educations
    educations = session.exec(
        select(Education).where(Education.user_id == user.id)
    ).all()

    return templates.TemplateResponse(
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

