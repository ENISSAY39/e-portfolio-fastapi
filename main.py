"""Create and configure the FastAPI e-portfolio application.

This module is deliberately limited to application wiring: database migrations
and optional demo data run during startup, middleware prepares CSRF protection,
and each domain router is registered on the shared application instance.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.csrf import get_or_create_csrf_token, set_csrf_cookie
from core.database import run_database_migrations
from routers import auth, user, experience, education
from seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare persistent application state before accepting HTTP requests.

    Alembic must finish first so route handlers never execute against an older
    schema. Demo data is then synchronized only when the active environment has
    explicitly enabled it (or when development defaults apply).
    """
    # Apply committed migrations instead of relying on ``create_all()``, which
    # cannot safely evolve tables that already contain user data.
    run_database_migrations()
    if settings.seed_demo_data_enabled:
        seed()

    # Control returns to FastAPI for the complete lifetime of the application.
    yield


# Passing the lifespan explicitly makes startup preparation part of FastAPI's
# supported lifecycle rather than relying on deprecated startup events.
app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def csrf_cookie_middleware(request: Request, call_next):
    """Make one CSRF token available to templates and the browser cookie jar.

    Mutating routes compare their submitted form token with this HTTP-only
    cookie. The middleware reuses a plausible existing token to avoid changing
    it between displaying a form and submitting that same form.
    """
    csrf_token = get_or_create_csrf_token(request)
    # Templates read the token through ``request.state.csrf_token`` and place it
    # in a hidden form field; JavaScript does not need access to the cookie.
    request.state.csrf_token = csrf_token
    response = await call_next(request)

    # Only emit Set-Cookie when the client has no token (or sent an invalid one)
    # so normal requests do not unnecessarily refresh the cookie lifetime.
    if request.cookies.get("csrf_token") != csrf_token:
        set_csrf_cookie(response, csrf_token)
    return response


# Expose stylesheets and other public assets under a stable URL prefix.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register the public/authentication, profile, experience, and education routes.
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(experience.router)
app.include_router(education.router)
