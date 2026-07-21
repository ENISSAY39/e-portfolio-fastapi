"""Routes de création de compte et d'affichage des profils privés ou publics."""

from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from core.authentication import get_authenticated_user
from core.config import settings
from core.csrf import validate_csrf_token
from core.database import get_session
from core.security import create_access_token, hash_password
from core.validation import (
    clean_optional_text,
    clean_text,
    normalize_email,
    normalize_phone,
    parse_birth_date,
    validate_password,
)

from schemas.Education import Education
from schemas.Experiences import Experience
from schemas.Links import ExternalLink
from schemas.Projects import Project
from schemas.Skills import Skill
from schemas.User import User

# Ce routeur regroupe les opérations centrées sur un utilisateur et son portfolio.
router = APIRouter()

# Les pages de compte sont rendues côté serveur depuis le dossier templates/.
templates = Jinja2Templates(directory="templates")


def calculate_age(birth_date: date) -> int:
    """Calcule l'âge révolu à la date du jour depuis une date de naissance."""

    today_date = date.today()
    age = today_date.year - birth_date.year

    # L'écart d'années doit être réduit si l'anniversaire n'est pas encore passé cette année.
    if (today_date.month, today_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


@router.get("/portfolio/{user_id}", response_class=HTMLResponse)
def public_portfolio(
    request: Request,
    user_id: int,
    session: Session = Depends(get_session),
):
    """Affiche le portfolio public identifié par son identifiant utilisateur."""

    # La clé primaire de l'URL permet un accès direct sans authentification.
    user = session.get(User, user_id)

    # Un identifiant inconnu ne doit pas être transmis au template de profil.
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Les expériences affichées appartiennent exclusivement au compte demandé.
    experiences = session.exec(
        select(Experience).where(Experience.user_id == user.id)
    ).all()

    # Les formations sont chargées séparément avec le même filtre de propriétaire.
    educations = session.exec(
        select(Education).where(Education.user_id == user.id)
    ).all()

    skills = session.exec(
        select(Skill).where(Skill.user_id == user.id).order_by(Skill.id)
    ).all()
    projects = session.exec(
        select(Project).where(Project.user_id == user.id).order_by(Project.id)
    ).all()
    links = session.exec(
        select(ExternalLink)
        .where(ExternalLink.user_id == user.id)
        .order_by(ExternalLink.id)
    ).all()

    # Le template public reçoit l'utilisateur et les deux collections de son portfolio.
    return templates.TemplateResponse(
        request,
        "public_profile.html",
        {
            "request": request,
            "user": user,
            "experiences": experiences,
            "educations": educations,
            "skills": skills,
            "projects": projects,
            "links": links,
        },
    )


@router.get("/create_user", response_class=HTMLResponse)
def show_form(request: Request):
    """Affiche un formulaire d'inscription vide."""

    # form_data permet au même template d'afficher un formulaire vide ou de restaurer une saisie.
    return templates.TemplateResponse(
        request,
        "create_user.html",
        {"request": request, "form_data": {}},
    )


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
    """Valide une inscription, crée le compte et redirige vers la connexion."""

    # Le jeton lié au navigateur est vérifié avant de traiter les données du formulaire.
    validate_csrf_token(request, csrf_token)

    # Les champs non sensibles sont conservés pour réafficher la saisie après une erreur.
    # Le mot de passe est volontairement exclu afin de ne jamais le renvoyer au template.
    form_data = {
        "name": name,
        "first_name": first_name,
        "birth_date": birth_date,
        "mail": mail,
        "phone": phone,
    }

    # Chaque valeur est nettoyée et validée avant la construction de l'objet SQLModel.
    try:
        cleaned_name = clean_text(name, "Name", 100)
        cleaned_first_name = clean_text(first_name, "First name", 100)
        birth_date_obj = parse_birth_date(birth_date)
        normalized_mail = normalize_email(mail)
        normalized_phone = normalize_phone(phone)
        validated_password = validate_password(password)
    except ValueError as exc:
        # Les erreurs attendues de validation sont présentées avec un statut client 400.
        return templates.TemplateResponse(
            request,
            "create_user.html",
            {"request": request, "error": str(exc), "form_data": form_data},
            status_code=400,
        )

    # Ce contrôle fournit une erreur lisible avant de tenter l'insertion en base.
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

    # Seul le condensat du mot de passe validé est enregistré ; le mot de passe brut est écarté.
    user = User(
        name=cleaned_name,
        first_name=cleaned_first_name,
        birth_date=birth_date_obj,
        mail=normalized_mail,
        phone=normalized_phone,
        hashed_password=hash_password(validated_password),
    )

    # L'ajout reste en attente dans la session jusqu'à la transaction commitée ci-dessous.
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        # La contrainte unique protège aussi contre deux inscriptions concurrentes.
        # Un rollback est obligatoire avant de pouvoir réutiliser cette session SQLAlchemy.
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

    # Post/Redirect/Get évite de recréer le compte si la page est actualisée.
    return RedirectResponse("/login", status_code=303)


@router.get("/profil", response_class=HTMLResponse)
def show_profile(
    request: Request,
    session: Session = Depends(get_session),
):
    """Affiche le tableau de bord privé du compte authentifié."""

    # Le cookie JWT est décodé puis son sujet est résolu en utilisateur par le helper partagé.
    user = get_authenticated_user(request, session)
    if not user:
        # Un cookie absent, invalide, expiré ou associé à aucun compte ramène à la connexion.
        return RedirectResponse("/login", status_code=303)

    # L'identifiant issu du compte authentifié borne la lecture à ses propres expériences.
    experiences = session.exec(
        select(Experience).where(Experience.user_id == user.id)
    ).all()

    # Les formations sont filtrées avec la même règle de propriété.
    educations = session.exec(
        select(Education).where(Education.user_id == user.id)
    ).all()

    skills = session.exec(
        select(Skill).where(Skill.user_id == user.id).order_by(Skill.id)
    ).all()
    projects = session.exec(
        select(Project).where(Project.user_id == user.id).order_by(Project.id)
    ).all()
    links = session.exec(
        select(ExternalLink)
        .where(ExternalLink.user_id == user.id)
        .order_by(ExternalLink.id)
    ).all()

    # Le template privé reçoit uniquement les informations du compte résolu par le JWT.
    response = templates.TemplateResponse(
        request,
        "profil.html",
        {
            "request": request,
            "user": user,
            "name": user.name,
            "first_name": user.first_name,
            "age": calculate_age(user.birth_date),
            "mail": user.mail,
            "phone": user.phone,
            "bio": user.bio,
            "experiences": experiences,
            "educations": educations,
            "skills": skills,
            "projects": projects,
            "links": links,
        },
    )

    # Le profil privé ne doit pas rester visible via l'historique après une déconnexion.
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@router.get("/profil/edit", response_class=HTMLResponse)
def show_profile_edit_form(
    request: Request,
    session: Session = Depends(get_session),
):
    """Display the identity, contact, and biography form for the current user."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "profile_edit.html",
        {"request": request, "user": user, "form_values": {}},
    )


@router.post("/profil/edit")
def update_profile(
    request: Request,
    csrf_token: str = Form(""),
    name: str = Form(...),
    first_name: str = Form(...),
    birth_date: str = Form(...),
    mail: str = Form(...),
    phone: str = Form(...),
    bio: str = Form(""),
    session: Session = Depends(get_session),
):
    """Validate and update the authenticated user's editable profile fields."""
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    validate_csrf_token(request, csrf_token)
    form_values = {
        "name": name,
        "first_name": first_name,
        "birth_date": birth_date,
        "mail": mail,
        "phone": phone,
        "bio": bio,
    }

    try:
        cleaned_name = clean_text(name, "Name", 100)
        cleaned_first_name = clean_text(first_name, "First name", 100)
        parsed_birth_date = parse_birth_date(birth_date)
        normalized_mail = normalize_email(mail)
        normalized_phone = normalize_phone(phone)
        cleaned_bio = clean_optional_text(bio, "Biography", 3000)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "profile_edit.html",
            {
                "request": request,
                "user": user,
                "error": str(exc),
                "form_values": form_values,
            },
            status_code=400,
        )

    duplicate = session.exec(
        select(User).where(
            User.mail == normalized_mail,
            User.id != user.id,
        )
    ).first()
    if duplicate:
        return templates.TemplateResponse(
            request,
            "profile_edit.html",
            {
                "request": request,
                "user": user,
                "error": "An account already exists with this email address.",
                "form_values": form_values,
            },
            status_code=409,
        )

    user_id = user.id
    user.name = cleaned_name
    user.first_name = cleaned_first_name
    user.birth_date = parsed_birth_date
    user.mail = normalized_mail
    user.phone = normalized_phone
    user.bio = cleaned_bio

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        user = session.get(User, user_id)
        return templates.TemplateResponse(
            request,
            "profile_edit.html",
            {
                "request": request,
                "user": user,
                "error": "An account already exists with this email address.",
                "form_values": form_values,
            },
            status_code=409,
        )

    # The email is the JWT subject, so every successful profile update renews
    # the cookie and keeps authentication valid even when that email changed.
    token = create_access_token(data={"sub": normalized_mail})
    response = RedirectResponse("/profil", status_code=303)
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
