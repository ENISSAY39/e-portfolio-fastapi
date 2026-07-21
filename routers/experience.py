"""Routes protégées de création, consultation, modification et suppression d'expériences."""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from core.authentication import get_authenticated_user
from core.csrf import validate_csrf_token
from core.database import get_session
from core.validation import clean_text, parse_date_range
from schemas.Experiences import Experience

# Ce routeur expose les opérations CRUD des expériences professionnelles.
router = APIRouter()

# Le même template prend en charge la création et l'édition grâce à la valeur exp.
templates = Jinja2Templates(directory="templates")


@router.get("/profil/experience", response_class=HTMLResponse)
def show_experience_form(
    request: Request,
    session: Session = Depends(get_session),
):
    """Affiche le formulaire vide de création d'une expérience authentifiée."""

    # L'utilisateur est résolu depuis le cookie JWT avant d'exposer une page privée.
    user = get_authenticated_user(request, session)
    if not user:
        # Tout échec d'authentification conserve le comportement de redirection vers la connexion.
        return RedirectResponse("/login", status_code=303)

    # exp=None place le template partagé en mode création et form_values initialise les champs.
    return templates.TemplateResponse(
        request,
        "experience.html",
        {"request": request, "exp": None, "form_values": {}},
    )


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
    """Valide et enregistre une expérience pour l'utilisateur authentifié."""

    # Le propriétaire est toujours dérivé du JWT, jamais d'une valeur fournie par le formulaire.
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # La mutation n'est autorisée qu'avec le jeton CSRF associé au navigateur courant.
    validate_csrf_token(request, csrf_token)

    # La saisie brute est conservée uniquement pour réafficher le formulaire en cas d'erreur.
    form_values = {
        "title": title,
        "date_start": date_start,
        "date_end": date_end,
        "description": description,
        "company": company,
    }

    # Les textes sont nettoyés et bornés ; la plage vérifie le format et l'ordre des dates.
    try:
        cleaned_title = clean_text(title, "Title", 150)
        cleaned_description = clean_text(description, "Description", 3000)
        cleaned_company = clean_text(company, "Company", 150)
        parsed_start, parsed_end = parse_date_range(date_start, date_end)
    except ValueError as exc:
        # Le template reste en mode création et présente l'erreur de validation au client.
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

    # user_id provient exclusivement du compte authentifié et établit la propriété en base.
    experience = Experience(
        title=cleaned_title,
        date_start=parsed_start,
        date_end=parsed_end,
        description=cleaned_description,
        company=cleaned_company,
        user_id=user.id,
    )

    # La session injectée regroupe l'insertion et sa validation dans la requête courante.
    session.add(experience)
    session.commit()

    # Le code 303 évite de soumettre une seconde fois le formulaire lors d'une actualisation.
    return RedirectResponse("/profil", status_code=303)


@router.post("/profil/experience/delete/{exp_id}")
def delete_experience(
    request: Request,
    exp_id: int,
    csrf_token: str = Form(""),
    session: Session = Depends(get_session),
):
    """Supprime une expérience uniquement si elle appartient au compte authentifié."""

    # La suppression exige d'abord une identité valide issue du cookie d'accès.
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Le contrôle CSRF précède le chargement de la ressource destinée à être supprimée.
    validate_csrf_token(request, csrf_token)

    # La clé primaire vient de l'URL, mais elle ne constitue jamais une preuve de propriété.
    exp = session.get(Experience, exp_id)

    # Une ressource absente ou appartenant à un autre compte est laissée intacte.
    if exp and user and exp.user_id == user.id:
        session.delete(exp)
        session.commit()

    # La réponse identique masque l'existence des ressources étrangères et applique PRG.
    return RedirectResponse("/profil", status_code=303)


@router.get("/profil/experience/edit/{exp_id}", response_class=HTMLResponse)
def edit_experience_form(
    request: Request,
    exp_id: int,
    session: Session = Depends(get_session),
):
    """Affiche le formulaire d'édition d'une expérience possédée par le compte courant."""

    # Le profil actif est résolu avant de charger une donnée privée.
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # L'objet demandé est chargé par sa clé primaire dans la session de la requête.
    exp = session.get(Experience, exp_id)

    # Le contrôle d'ownership interdit l'affichage d'une expérience appartenant à autrui.
    if not exp or not user or exp.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    # exp active le mode édition du template ; les valeurs persistées préremplissent les champs.
    return templates.TemplateResponse(
        request,
        "experience.html",
        {"request": request, "exp": exp, "form_values": {}},
    )


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
    """Valide puis met à jour une expérience appartenant au compte authentifié."""

    # L'identité chargée depuis le JWT est nécessaire avant toute modification.
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Le jeton CSRF protège la requête POST contre une soumission depuis un site tiers.
    validate_csrf_token(request, csrf_token)

    # L'identifiant d'URL sert uniquement à charger la ressource candidate.
    exp = session.get(Experience, exp_id)

    # La propriété est vérifiée avant même de valider ou d'appliquer les nouvelles valeurs.
    if not exp or exp.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    # La saisie d'origine permet de ne pas effacer les champs après une validation refusée.
    form_values = {
        "title": title,
        "date_start": date_start,
        "date_end": date_end,
        "description": description,
        "company": company,
    }

    # Les mêmes règles qu'à la création maintiennent des données cohérentes après l'édition.
    try:
        cleaned_title = clean_text(title, "Title", 150)
        cleaned_description = clean_text(description, "Description", 3000)
        cleaned_company = clean_text(company, "Company", 150)
        parsed_start, parsed_end = parse_date_range(date_start, date_end)
    except ValueError as exc:
        # L'objet exp conserve le mode édition pendant que form_values restaure la saisie invalide.
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

    # Les valeurs validées remplacent les champs de l'entité déjà suivie par la session.
    exp.title = cleaned_title
    exp.date_start = parsed_start
    exp.date_end = parsed_end
    exp.description = cleaned_description
    exp.company = cleaned_company

    # commit persiste toutes les modifications atomiquement dans la base configurée.
    session.commit()

    # Le navigateur revient au profil par un GET distinct après la mise à jour.
    return RedirectResponse("/profil", status_code=303)
