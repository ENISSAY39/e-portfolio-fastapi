"""Owned CRUD routes for skills, projects, and external portfolio links."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from core.authentication import get_authenticated_user
from core.csrf import validate_csrf_token
from core.database import get_session
from core.validation import (
    clean_optional_text,
    clean_text,
    parse_skill_level,
    validate_http_url,
)
from schemas.Links import ExternalLink
from schemas.Projects import Project
from schemas.Skills import Skill


router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/profil/skill", response_class=HTMLResponse)
def show_skill_form(
    request: Request,
    session: Session = Depends(get_session),
):
    """Display a blank skill form for the authenticated user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "skill.html",
        {"request": request, "skill": None, "form_values": {}},
    )


@router.post("/profil/skill")
def create_skill(
    request: Request,
    csrf_token: str = Form(""),
    name: str = Form(...),
    level: str = Form(...),
    session: Session = Depends(get_session),
):
    """Create a validated skill owned by the authenticated user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    form_values = {"name": name, "level": level}
    try:
        cleaned_name = clean_text(name, "Skill name", 100)
        parsed_level = parse_skill_level(level)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "skill.html",
            {
                "request": request,
                "skill": None,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    session.add(Skill(name=cleaned_name, level=parsed_level, user_id=user.id))
    session.commit()
    return RedirectResponse("/profil", status_code=303)


@router.get("/profil/skill/edit/{skill_id}", response_class=HTMLResponse)
def show_skill_edit_form(
    request: Request,
    skill_id: int,
    session: Session = Depends(get_session),
):
    """Display the edit form only for a skill owned by the current user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    skill = session.get(Skill, skill_id)
    if not skill or skill.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    return templates.TemplateResponse(
        request,
        "skill.html",
        {"request": request, "skill": skill, "form_values": {}},
    )


@router.post("/profil/skill/edit/{skill_id}")
def update_skill(
    request: Request,
    skill_id: int,
    csrf_token: str = Form(""),
    name: str = Form(...),
    level: str = Form(...),
    session: Session = Depends(get_session),
):
    """Update a skill after authenticating and verifying its ownership."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    skill = session.get(Skill, skill_id)
    if not skill or skill.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    form_values = {"name": name, "level": level}
    try:
        cleaned_name = clean_text(name, "Skill name", 100)
        parsed_level = parse_skill_level(level)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "skill.html",
            {
                "request": request,
                "skill": skill,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    skill.name = cleaned_name
    skill.level = parsed_level
    session.commit()
    return RedirectResponse("/profil", status_code=303)


@router.post("/profil/skill/delete/{skill_id}")
def delete_skill(
    request: Request,
    skill_id: int,
    csrf_token: str = Form(""),
    session: Session = Depends(get_session),
):
    """Delete a skill only when it belongs to the authenticated user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    skill = session.get(Skill, skill_id)
    if skill and skill.user_id == user.id:
        session.delete(skill)
        session.commit()
    return RedirectResponse("/profil", status_code=303)


@router.get("/profil/project", response_class=HTMLResponse)
def show_project_form(
    request: Request,
    session: Session = Depends(get_session),
):
    """Display a blank project form for the authenticated user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "project.html",
        {"request": request, "project": None, "form_values": {}},
    )


@router.post("/profil/project")
def create_project(
    request: Request,
    csrf_token: str = Form(""),
    title: str = Form(...),
    description: str = Form(...),
    technologies: str = Form(""),
    project_url: str = Form(""),
    repository_url: str = Form(""),
    session: Session = Depends(get_session),
):
    """Create a validated project owned by the authenticated user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    form_values = {
        "title": title,
        "description": description,
        "technologies": technologies,
        "project_url": project_url,
        "repository_url": repository_url,
    }
    try:
        cleaned_title = clean_text(title, "Project title", 150)
        cleaned_description = clean_text(description, "Description", 5000)
        cleaned_technologies = clean_optional_text(
            technologies,
            "Technologies",
            500,
        )
        cleaned_project_url = validate_http_url(project_url, "Project URL")
        cleaned_repository_url = validate_http_url(
            repository_url,
            "Repository URL",
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "project.html",
            {
                "request": request,
                "project": None,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    session.add(
        Project(
            title=cleaned_title,
            description=cleaned_description,
            technologies=cleaned_technologies,
            project_url=cleaned_project_url,
            repository_url=cleaned_repository_url,
            user_id=user.id,
        )
    )
    session.commit()
    return RedirectResponse("/profil", status_code=303)


@router.get("/profil/project/edit/{project_id}", response_class=HTMLResponse)
def show_project_edit_form(
    request: Request,
    project_id: int,
    session: Session = Depends(get_session),
):
    """Display the edit form only for an owned project."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    project = session.get(Project, project_id)
    if not project or project.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    return templates.TemplateResponse(
        request,
        "project.html",
        {"request": request, "project": project, "form_values": {}},
    )


@router.post("/profil/project/edit/{project_id}")
def update_project(
    request: Request,
    project_id: int,
    csrf_token: str = Form(""),
    title: str = Form(...),
    description: str = Form(...),
    technologies: str = Form(""),
    project_url: str = Form(""),
    repository_url: str = Form(""),
    session: Session = Depends(get_session),
):
    """Update a project after authenticating and checking ownership."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    project = session.get(Project, project_id)
    if not project or project.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    form_values = {
        "title": title,
        "description": description,
        "technologies": technologies,
        "project_url": project_url,
        "repository_url": repository_url,
    }
    try:
        cleaned_title = clean_text(title, "Project title", 150)
        cleaned_description = clean_text(description, "Description", 5000)
        cleaned_technologies = clean_optional_text(
            technologies,
            "Technologies",
            500,
        )
        cleaned_project_url = validate_http_url(project_url, "Project URL")
        cleaned_repository_url = validate_http_url(
            repository_url,
            "Repository URL",
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "project.html",
            {
                "request": request,
                "project": project,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    project.title = cleaned_title
    project.description = cleaned_description
    project.technologies = cleaned_technologies
    project.project_url = cleaned_project_url
    project.repository_url = cleaned_repository_url
    session.commit()
    return RedirectResponse("/profil", status_code=303)


@router.post("/profil/project/delete/{project_id}")
def delete_project(
    request: Request,
    project_id: int,
    csrf_token: str = Form(""),
    session: Session = Depends(get_session),
):
    """Delete a project only when it belongs to the authenticated user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    project = session.get(Project, project_id)
    if project and project.user_id == user.id:
        session.delete(project)
        session.commit()
    return RedirectResponse("/profil", status_code=303)


@router.get("/profil/link", response_class=HTMLResponse)
def show_link_form(
    request: Request,
    session: Session = Depends(get_session),
):
    """Display a blank external-link form for the authenticated user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "link.html",
        {"request": request, "link": None, "form_values": {}},
    )


@router.post("/profil/link")
def create_link(
    request: Request,
    csrf_token: str = Form(""),
    label: str = Form(...),
    url: str = Form(...),
    session: Session = Depends(get_session),
):
    """Create a validated external link for the authenticated user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    form_values = {"label": label, "url": url}
    try:
        cleaned_label = clean_text(label, "Link label", 100)
        cleaned_url = validate_http_url(url, "URL", required=True)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "link.html",
            {
                "request": request,
                "link": None,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    # ``required=True`` guarantees a string; keep the assertion close to the
    # construction so type checkers and readers can see that invariant.
    assert cleaned_url is not None
    session.add(
        ExternalLink(label=cleaned_label, url=cleaned_url, user_id=user.id)
    )
    session.commit()
    return RedirectResponse("/profil", status_code=303)


@router.get("/profil/link/edit/{link_id}", response_class=HTMLResponse)
def show_link_edit_form(
    request: Request,
    link_id: int,
    session: Session = Depends(get_session),
):
    """Display the edit form only for an owned external link."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    link = session.get(ExternalLink, link_id)
    if not link or link.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    return templates.TemplateResponse(
        request,
        "link.html",
        {"request": request, "link": link, "form_values": {}},
    )


@router.post("/profil/link/edit/{link_id}")
def update_link(
    request: Request,
    link_id: int,
    csrf_token: str = Form(""),
    label: str = Form(...),
    url: str = Form(...),
    session: Session = Depends(get_session),
):
    """Update an external link after verifying its owner."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    link = session.get(ExternalLink, link_id)
    if not link or link.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    form_values = {"label": label, "url": url}
    try:
        cleaned_label = clean_text(label, "Link label", 100)
        cleaned_url = validate_http_url(url, "URL", required=True)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "link.html",
            {
                "request": request,
                "link": link,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    assert cleaned_url is not None
    link.label = cleaned_label
    link.url = cleaned_url
    session.commit()
    return RedirectResponse("/profil", status_code=303)


@router.post("/profil/link/delete/{link_id}")
def delete_link(
    request: Request,
    link_id: int,
    csrf_token: str = Form(""),
    session: Session = Depends(get_session),
):
    """Delete an external link only when it belongs to the current user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    link = session.get(ExternalLink, link_id)
    if link and link.user_id == user.id:
        session.delete(link)
        session.commit()
    return RedirectResponse("/profil", status_code=303)
