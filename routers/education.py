"""Routes protégées de création, consultation, modification et suppression de formations."""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from core.authentication import get_authenticated_user
from core.csrf import validate_csrf_token
from core.database import get_session
from core.validation import clean_text, parse_date_range
from schemas.Education import Education

# Ce routeur expose les opérations CRUD des parcours de formation.
router = APIRouter()

# Le même template prend en charge la création et l'édition grâce à la valeur edu.
templates = Jinja2Templates(directory="templates")


@router.get("/profil/education", response_class=HTMLResponse)
def show_form(
    request: Request,
    session: Session = Depends(get_session),
):
    """Affiche le formulaire vide de création d'une formation authentifiée."""

    # L'utilisateur est résolu depuis le cookie JWT avant d'exposer une page privée.
    user = get_authenticated_user(request, session)
    if not user:
        # Tout échec d'authentification conserve le comportement de redirection vers la connexion.
        return RedirectResponse("/login", status_code=303)

    # edu=None place le template partagé en mode création et form_values initialise les champs.
    return templates.TemplateResponse(
        request,
        "education.html",
        {"request": request, "edu": None, "form_values": {}},
    )


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
    """Valide et enregistre une formation pour l'utilisateur authentifié."""

    # Le propriétaire est toujours dérivé du JWT, jamais d'une valeur fournie par le formulaire.
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # La mutation n'est autorisée qu'avec le jeton CSRF associé au navigateur courant.
    validate_csrf_token(request, csrf_token)

    # La saisie brute est conservée uniquement pour réafficher le formulaire en cas d'erreur.
    form_values = {
        "school_name": school_name,
        "date_start": date_start,
        "date_end": date_end,
        "description": description,
        "major": major,
    }

    # Les textes sont nettoyés et bornés ; la plage vérifie le format et l'ordre des dates.
    try:
        cleaned_school_name = clean_text(school_name, "School", 150)
        cleaned_description = clean_text(description, "Description", 3000)
        cleaned_major = clean_text(major, "Major", 150)
        parsed_start, parsed_end = parse_date_range(date_start, date_end)
    except ValueError as exc:
        # Le template reste en mode création et présente l'erreur de validation au client.
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

    # user_id provient exclusivement du compte authentifié et établit la propriété en base.
    education = Education(
        school_name=cleaned_school_name,
        date_start=parsed_start,
        date_end=parsed_end,
        description=cleaned_description,
        major=cleaned_major,
        user_id=user.id,
    )

    # La session injectée regroupe l'insertion et sa validation dans la requête courante.
    session.add(education)
    session.commit()

    # Le code 303 évite de soumettre une seconde fois le formulaire lors d'une actualisation.
    return RedirectResponse("/profil", status_code=303)


@router.post("/profil/education/delete/{edu_id}")
def delete_education(
    request: Request,
    edu_id: int,
    csrf_token: str = Form(""),
    session: Session = Depends(get_session),
):
    """Supprime une formation uniquement si elle appartient au compte authentifié."""

    # La suppression exige d'abord une identité valide issue du cookie d'accès.
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Le contrôle CSRF précède le chargement de la ressource destinée à être supprimée.
    validate_csrf_token(request, csrf_token)

    # La clé primaire vient de l'URL, mais elle ne constitue jamais une preuve de propriété.
    edu = session.get(Education, edu_id)

    # Une ressource absente ou appartenant à un autre compte est laissée intacte.
    if edu and user and edu.user_id == user.id:
        session.delete(edu)
        session.commit()

    # La réponse identique masque l'existence des ressources étrangères et applique PRG.
    return RedirectResponse("/profil", status_code=303)


@router.get("/profil/education/edit/{edu_id}", response_class=HTMLResponse)
def edit_education_form(
    request: Request,
    edu_id: int,
    session: Session = Depends(get_session),
):
    """Affiche le formulaire d'édition d'une formation possédée par le compte courant."""

    # Le profil actif est résolu avant de charger une donnée privée.
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # L'objet demandé est chargé par sa clé primaire dans la session de la requête.
    edu = session.get(Education, edu_id)

    # Le contrôle d'ownership interdit l'affichage d'une formation appartenant à autrui.
    if not edu or not user or edu.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    # edu active le mode édition du template ; les valeurs persistées préremplissent les champs.
    return templates.TemplateResponse(
        request,
        "education.html",
        {"request": request, "edu": edu, "form_values": {}},
    )


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
    """Valide puis met à jour une formation appartenant au compte authentifié."""

    # L'identité chargée depuis le JWT est nécessaire avant toute modification.
    user = get_authenticated_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Le jeton CSRF protège la requête POST contre une soumission depuis un site tiers.
    validate_csrf_token(request, csrf_token)

    # L'identifiant d'URL sert uniquement à charger la ressource candidate.
    edu = session.get(Education, edu_id)

    # La propriété est vérifiée avant même de valider ou d'appliquer les nouvelles valeurs.
    if not edu or edu.user_id != user.id:
        return RedirectResponse("/profil", status_code=303)

    # La saisie d'origine permet de ne pas effacer les champs après une validation refusée.
    form_values = {
        "school_name": school_name,
        "date_start": date_start,
        "date_end": date_end,
        "description": description,
        "major": major,
    }

    # Les mêmes règles qu'à la création maintiennent des données cohérentes après l'édition.
    try:
        cleaned_school_name = clean_text(school_name, "School", 150)
        cleaned_description = clean_text(description, "Description", 3000)
        cleaned_major = clean_text(major, "Major", 150)
        parsed_start, parsed_end = parse_date_range(date_start, date_end)
    except ValueError as exc:
        # L'objet edu conserve le mode édition pendant que form_values restaure la saisie invalide.
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

    # Les valeurs validées remplacent les champs de l'entité déjà suivie par la session.
    edu.school_name = cleaned_school_name
    edu.date_start = parsed_start
    edu.date_end = parsed_end
    edu.description = cleaned_description
    edu.major = cleaned_major

    # commit persiste toutes les modifications atomiquement dans la base configurée.
    session.commit()

    # Le navigateur revient au profil par un GET distinct après la mise à jour.
    return RedirectResponse("/profil", status_code=303)
