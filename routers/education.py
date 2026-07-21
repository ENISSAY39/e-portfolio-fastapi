from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from core.authentication import get_authenticated_user
from core.csrf import validate_csrf_token
from core.database import get_session
from core.validation import clean_text, parse_date_range
from schemas.Education import Education

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# FORM CREATE
@router.get("/profil/education", response_class=HTMLResponse)
def show_form(
    request: Request,
    session: Session = Depends(get_session),
):
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "education.html",
        {"request": request, "edu": None, "form_values": {}},
    )


# CREATE
@router.post("/profil/education")
def create_education(
    request: Request,
    csrf_token: str = Form(""),
    school_name: str = Form(...),
    date_start: str = Form(...),
    date_end: str = Form(...),
    description: str = Form(...),
    major: str = Form(...),
    session: Session = Depends(get_session),
):
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    form_values = {
        "school_name": school_name,
        "date_start": date_start,
        "date_end": date_end,
        "description": description,
        "major": major,
    }
    try:
        cleaned_school_name = clean_text(school_name, "School", 150)
        cleaned_description = clean_text(description, "Description", 3000)
        cleaned_major = clean_text(major, "Major", 150)
        parsed_start, parsed_end = parse_date_range(date_start, date_end)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "education.html",
            {
                "request": request,
                "edu": None,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    education = Education(
        school_name=cleaned_school_name,
        date_start=parsed_start,
        date_end=parsed_end,
        description=cleaned_description,
        major=cleaned_major,
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
    csrf_token: str = Form(""),
    session: Session = Depends(get_session),
):
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
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
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    edu = session.get(Education, edu_id)

    if not edu or not user or edu.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    return templates.TemplateResponse(
        request,
        "education.html",
        {"request": request, "edu": edu, "form_values": {}},
    )


# UPDATE
@router.post("/profil/education/edit/{edu_id}")
def update_education(
    request: Request,
    edu_id: int,
    csrf_token: str = Form(""),
    school_name: str = Form(...),
    date_start: str = Form(...),
    date_end: str = Form(...),
    description: str = Form(...),
    major: str = Form(...),
    session: Session = Depends(get_session),
):
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    edu = session.get(Education, edu_id)

    if not edu or edu.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    form_values = {
        "school_name": school_name,
        "date_start": date_start,
        "date_end": date_end,
        "description": description,
        "major": major,
    }
    try:
        cleaned_school_name = clean_text(school_name, "School", 150)
        cleaned_description = clean_text(description, "Description", 3000)
        cleaned_major = clean_text(major, "Major", 150)
        parsed_start, parsed_end = parse_date_range(date_start, date_end)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "education.html",
            {
                "request": request,
                "edu": edu,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    edu.school_name = cleaned_school_name
    edu.date_start = parsed_start
    edu.date_end = parsed_end
    edu.description = cleaned_description
    edu.major = cleaned_major
    session.commit()

    return RedirectResponse("/profil", status_code=303)
