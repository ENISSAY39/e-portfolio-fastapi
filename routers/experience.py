from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from core.authentication import get_authenticated_user
from core.csrf import validate_csrf_token
from core.database import get_session
from core.validation import clean_text, parse_date_range
from schemas.Experiences import Experience

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# Form CREATE
@router.get("/profil/experience", response_class=HTMLResponse)
def show_experience_form(
    request: Request,
    session: Session = Depends(get_session),
):
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "experience.html",
        {"request": request, "exp": None, "form_values": {}},
    )


# CREATE
@router.post("/profil/experience")
def create_experience(
    request: Request,
    csrf_token: str = Form(""),
    title: str = Form(...),
    date_start: str = Form(...),
    date_end: str = Form(...),
    description: str = Form(...),
    company: str = Form(...),
    session: Session = Depends(get_session),
):
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    form_values = {
        "title": title,
        "date_start": date_start,
        "date_end": date_end,
        "description": description,
        "company": company,
    }
    try:
        cleaned_title = clean_text(title, "Title", 150)
        cleaned_description = clean_text(description, "Description", 3000)
        cleaned_company = clean_text(company, "Company", 150)
        parsed_start, parsed_end = parse_date_range(date_start, date_end)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "experience.html",
            {
                "request": request,
                "exp": None,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    experience = Experience(
        title=cleaned_title,
        date_start=parsed_start,
        date_end=parsed_end,
        description=cleaned_description,
        company=cleaned_company,
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
    csrf_token: str = Form(""),
    session: Session = Depends(get_session),
):
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)

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
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    exp = session.get(Experience, exp_id)

    if not exp or not user or exp.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    return templates.TemplateResponse(
        request,
        "experience.html",
        {"request": request, "exp": exp, "form_values": {}},
    )


# UPDATE
@router.post("/profil/experience/edit/{exp_id}")
def update_experience(
    request: Request,
    exp_id: int,
    csrf_token: str = Form(""),
    title: str = Form(...),
    date_start: str = Form(...),
    date_end: str = Form(...),
    description: str = Form(...),
    company: str = Form(...),
    session: Session = Depends(get_session),
):
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    exp = session.get(Experience, exp_id)

    if not exp or exp.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    form_values = {
        "title": title,
        "date_start": date_start,
        "date_end": date_end,
        "description": description,
        "company": company,
    }
    try:
        cleaned_title = clean_text(title, "Title", 150)
        cleaned_description = clean_text(description, "Description", 3000)
        cleaned_company = clean_text(company, "Company", 150)
        parsed_start, parsed_end = parse_date_range(date_start, date_end)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "experience.html",
            {
                "request": request,
                "exp": exp,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    exp.title = cleaned_title
    exp.date_start = parsed_start
    exp.date_end = parsed_end
    exp.description = cleaned_description
    exp.company = cleaned_company
    session.commit()

    return RedirectResponse("/profil", status_code=303)
