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
    run_database_migrations()
    if settings.seed_demo_data_enabled:
        seed()
    yield


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def csrf_cookie_middleware(request: Request, call_next):
    csrf_token = get_or_create_csrf_token(request)
    request.state.csrf_token = csrf_token
    response = await call_next(request)

    if request.cookies.get("csrf_token") != csrf_token:
        set_csrf_cookie(response, csrf_token)
    return response

# mount static files for css
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(experience.router)
app.include_router(education.router)
