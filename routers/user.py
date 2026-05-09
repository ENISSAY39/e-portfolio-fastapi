from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from core.database_2 import get_session
from core.security import hash_password, decode_access_token

from schemas.User import User
from schemas.Experiences import Experience
from schemas.Education import Education

router = APIRouter()
templates = Jinja2Templates(directory="templates")


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
    age: int = Form(...),
    mail: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):

    user = User(
        name=name,
        age=age,
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
            "age": user.age,
            "mail": user.mail,
            "phone": user.phone,
            "experiences": experiences,
            "educations": educations,
        },
    )

