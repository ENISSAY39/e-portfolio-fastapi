"""Routes publiques de découverte, de recherche et d'authentification."""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from core.config import settings
from core.csrf import CSRF_COOKIE_NAME, validate_csrf_token
from core.database import get_session
from core.security import verify_password, create_access_token
from core.validation import normalize_email
from schemas.User import User

# Ce routeur est enregistré dans l'application principale sans préfixe d'URL.
router = APIRouter()

# Les réponses HTML de ce module sont rendues depuis le dossier partagé templates/.
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    page: int = 1,
    session: Session = Depends(get_session),
):
    """Affiche la liste publique des portfolios avec une pagination de dix comptes."""

    # Une taille fixe garantit que les liens précédent/suivant restent cohérents.
    items_per_page = 10

    # Les numéros négatifs ou nuls sont ramenés à la première page.
    if page < 1:
        page = 1

    # Le total sert à calculer la dernière page accessible avant de lire la tranche.
    total_users = len(session.exec(select(User)).all())
    total_pages = (total_users + items_per_page - 1) // items_per_page

    # Une page trop grande est ramenée à la dernière page lorsqu'il existe des comptes.
    if page > total_pages and total_pages > 0:
        page = total_pages

    # SQL OFFSET est indexé à partir de zéro, contrairement au numéro visible par l'utilisateur.
    offset = (page - 1) * items_per_page

    # La session injectée est limitée à la requête HTTP et fournit uniquement la tranche courante.
    users = session.exec(select(User).offset(offset).limit(items_per_page)).all()

    # Le template reçoit les données et les indicateurs nécessaires à ses liens de pagination.
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "request": request,
            "users": users,
            "current_page": page,
            "total_pages": total_pages,
            "has_previous": page > 1,
            "has_next": page < total_pages,
            "previous_page": page - 1,
            "next_page": page + 1,
        },
    )


@router.get("/search", response_class=HTMLResponse)
def search_users(
    request: Request,
    query: str = "",
    page: int = 1,
    session: Session = Depends(get_session),
):
    """Recherche les portfolios par nom et affiche les résultats paginés."""

    # La recherche utilise la même taille de page que la page d'accueil.
    items_per_page = 10

    # Les numéros négatifs ou nuls sont ramenés à la première page.
    if page < 1:
        page = 1

    # La même condition de recherche est utilisée pour compter puis charger les résultats.
    total_users = len(session.exec(select(User).where(User.name.contains(query))).all())

    # Une recherche sans résultat conserve une page logique afin que le template reste navigable.
    total_pages = (
        (total_users + items_per_page - 1) // items_per_page if total_users > 0 else 1
    )

    # Une page située après les résultats est ramenée à la dernière page valide.
    if page > total_pages and total_pages > 0:
        page = total_pages

    # Le décalage SQL correspond au nombre de résultats des pages précédentes.
    offset = (page - 1) * items_per_page

    # Seule la tranche demandée est transmise au template de la page d'accueil.
    users = session.exec(
        select(User)
        .where(User.name.contains(query))
        .offset(offset)
        .limit(items_per_page)
    ).all()

    # La requête de recherche est conservée pour l'affichage et les liens de pagination.
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "request": request,
            "users": users,
            "query": query,
            "current_page": page,
            "total_pages": total_pages,
            "has_previous": page > 1,
            "has_next": page < total_pages,
            "previous_page": page - 1,
            "next_page": page + 1,
        },
    )


@router.get("/login", response_class=HTMLResponse)
def login_page_alias(request: Request):
    """Affiche le formulaire de connexion pour les visiteurs non authentifiés."""

    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request},
    )


@router.post("/login")
def login_user(
    request: Request,
    csrf_token: str = Form(""),
    mail: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    """Authentifie un compte et place son JWT dans un cookie HTTP-only."""

    # Toute mutation issue d'un formulaire doit provenir d'une page ayant reçu le jeton CSRF.
    validate_csrf_token(request, csrf_token)

    # La normalisation rend la recherche insensible aux espaces et à la casse usuels.
    try:
        normalized_mail = normalize_email(mail)
    except ValueError:
        # Une valeur mal formée suit quand même le chemin d'échec générique de connexion.
        normalized_mail = mail.strip().lower()

    # Le compte est recherché par son adresse normalisée dans la session de cette requête.
    user = session.exec(select(User).where(User.mail == normalized_mail)).first()

    # Un message unique évite de révéler si l'adresse existe dans la base.
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Invalid email or password.",
                "mail": normalized_mail,
            },
            status_code=401,
        )

    # L'adresse stockée devient le sujet du JWT et permettra de recharger le compte ensuite.
    token = create_access_token(data={"sub": user.mail})

    # Le code 303 applique Post/Redirect/Get et empêche la resoumission du mot de passe.
    response = RedirectResponse(
        url="/profil",
        status_code=303,
    )

    # Le navigateur peut envoyer le JWT, mais JavaScript ne peut pas lire ce cookie HTTP-only.
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


# Logout
@router.post("/logout")
def logout(request: Request, csrf_token: str = Form("")):
    """Déconnecte le navigateur en supprimant ses cookies d'accès et de protection CSRF."""

    # La déconnexion est une mutation protégée afin qu'un site tiers ne puisse pas la déclencher.
    validate_csrf_token(request, csrf_token)

    # La redirection 303 renvoie le navigateur vers l'accueil après le POST.
    response = RedirectResponse("/", status_code=303)

    # Les attributs doivent correspondre à ceux du cookie original pour garantir sa suppression.
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=settings.cookie_secure_enabled,
        httponly=True,
        samesite="lax",
    )

    # Un nouveau cycle de navigation générera un nouveau jeton CSRF après la déconnexion.
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        secure=settings.cookie_secure_enabled,
        httponly=True,
        samesite="lax",
    )
    return response
