from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import datetime

from core.database_2 import get_session
from core.security import decode_access_token
from schemas.Experiences import Experience
from schemas.User import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# Form CREATE
@router.get("/profil/experience", response_class=HTMLResponse)
def show_experience_form(request: Request):
    token = request.cookies.get("access_token")
    payload = decode_access_token(token)
    if not payload:
        return RedirectResponse("/login", status_code=303)

    mail = payload.get("sub")

    return templates.TemplateResponse(
        request,
        "experience.html",
        {"request": request, "exp": None, "mail": mail},
    )


# CREATE
@router.post("/profil/experience")
def create_experience(
    request: Request,
    title: str = Form(...),
    date_start: str = Form(...),
    date_end: str = Form(...),
    description: str = Form(...),
    company: str = Form(...),
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

    experience = Experience(
        title=title,
        date_start=datetime.strptime(date_start, "%Y-%m-%d"),
        date_end=datetime.strptime(date_end, "%Y-%m-%d"),
        description=description,
        company=company,
        user_id=user.id,
    )

    session.add(experience)
    session.commit()

    return RedirectResponse("/profil", status_code=303)


# DELETE
@router.post("/profil/experience/delete/{exp_id}")
def delete_experience(
    request: Request,
    exp_id: int,
    session: Session = Depends(get_session),
):
    token = request.cookies.get("access_token")
    payload = decode_access_token(token)
    if not payload:
        return RedirectResponse("/login", status_code=303)

    mail = payload.get("sub")
    user = session.exec(select(User).where(User.mail == mail)).first()

    exp = session.get(Experience, exp_id)

    if exp and user and exp.user_id == user.id:
        session.delete(exp)
        session.commit()

    return RedirectResponse("/profil", status_code=303)


# EDIT FORM
@router.get("/profil/experience/edit/{exp_id}", response_class=HTMLResponse)
def edit_experience_form(
    request: Request,
    exp_id: int,
    session: Session = Depends(get_session),
):
    token = request.cookies.get("access_token")
    payload = decode_access_token(token)
    if not payload:
        return RedirectResponse("/login", status_code=303)

    mail = payload.get("sub")
    user = session.exec(select(User).where(User.mail == mail)).first()
    exp = session.get(Experience, exp_id)

    if not exp or not user or exp.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    return templates.TemplateResponse(
        request,
        "experience.html",
        {"request": request, "exp": exp},
    )


# UPDATE
@router.post("/profil/experience/edit/{exp_id}")
def update_experience(
    request: Request,
    exp_id: int,
    title: str = Form(...),
    date_start: str = Form(...),
    date_end: str = Form(...),
    description: str = Form(...),
    company: str = Form(...),
    session: Session = Depends(get_session),
):
    token = request.cookies.get("access_token")
    payload = decode_access_token(token)
    if not payload:
        return RedirectResponse("/login", status_code=303)

    mail = payload.get("sub")
    user = session.exec(select(User).where(User.mail == mail)).first()
    exp = session.get(Experience, exp_id)

    if exp and user and exp.user_id == user.id:
        exp.title = title
        exp.date_start = datetime.strptime(date_start, "%Y-%m-%d")
        exp.date_end = datetime.strptime(date_end, "%Y-%m-%d")
        exp.description = description
        exp.company = company

        session.commit()

    return RedirectResponse("/profil", status_code=303)
