from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import datetime

from core.database_2 import get_session
from core.security import decode_access_token
from schemas.Education import Education
from schemas.User import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")

 
# FORM CREATE
@router.get("/profil/education", response_class=HTMLResponse)
def show_form(request: Request):
    token = request.cookies.get("access_token")
    payload = decode_access_token(token)
    if not payload:
        return RedirectResponse("/login", status_code=303)

    mail = payload.get("sub")

    return templates.TemplateResponse(
        request,
        "education.html",
        {"request": request, "edu": None, "mail": mail},
    )


# CREATE
@router.post("/profil/education")
def create_education(
    request: Request,
    school_name: str = Form(...),
    date_start: str = Form(...),
    date_end: str = Form(...),
    description: str = Form(...),
    major: str = Form(...),
    session: Session = Depends(get_session),
):
    token = request.cookies.get("access_token")
    payload = decode_access_token(token)
    if not payload:
        return RedirectResponse("/login", status_code=303)

    mail = payload.get("sub")
    user = session.exec(select(User).where(User.mail == mail)).first()

    if not user:
        return RedirectResponse("/", status_code=303)

    education = Education(
        school_name=school_name,
        date_start=datetime.strptime(date_start, "%Y-%m-%d"),
        date_end=datetime.strptime(date_end, "%Y-%m-%d"),
        description=description,
        major=major,
        user_id=user.id,
    )

    session.add(education)
    session.commit()

    return RedirectResponse("/profil", status_code=303)


# DELETE
@router.post("/profil/education/delete/{edu_id}")
def delete_education(
    request: Request,
    edu_id: int,
    session: Session = Depends(get_session),
):
    token = request.cookies.get("access_token")
    payload = decode_access_token(token)
    if not payload:
        return RedirectResponse("/login", status_code=303)

    mail = payload.get("sub")
    user = session.exec(select(User).where(User.mail == mail)).first()
    edu = session.get(Education, edu_id)

    if edu and user and edu.user_id == user.id:
        session.delete(edu)
        session.commit()

    return RedirectResponse("/profil", status_code=303)


# EDIT FORM
@router.get("/profil/education/edit/{edu_id}", response_class=HTMLResponse)
def edit_education_form(
    request: Request,
    edu_id: int,
    session: Session = Depends(get_session),
):
    token = request.cookies.get("access_token")
    payload = decode_access_token(token)
    if not payload:
        return RedirectResponse("/login", status_code=303)

    mail = payload.get("sub")
    user = session.exec(select(User).where(User.mail == mail)).first()
    edu = session.get(Education, edu_id)

    if not edu or not user or edu.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    return templates.TemplateResponse(
        request,
        "education.html",
        {"request": request, "edu": edu},
    )


# UPDATE
@router.post("/profil/education/edit/{edu_id}")
def update_education(
    request: Request,
    edu_id: int,
    school_name: str = Form(...),
    date_start: str = Form(...),
    date_end: str = Form(...),
    description: str = Form(...),
    major: str = Form(...),
    session: Session = Depends(get_session),
):
    token = request.cookies.get("access_token")
    payload = decode_access_token(token)
    if not payload:
        return RedirectResponse("/login", status_code=303)

    mail = payload.get("sub")
    user = session.exec(select(User).where(User.mail == mail)).first()
    edu = session.get(Education, edu_id)

    if edu and user and edu.user_id == user.id:
        edu.school_name = school_name
        edu.date_start = datetime.strptime(date_start, "%Y-%m-%d")
        edu.date_end = datetime.strptime(date_end, "%Y-%m-%d")
        edu.description = description
        edu.major = major

        session.commit()

    return RedirectResponse("/profil", status_code=303)
