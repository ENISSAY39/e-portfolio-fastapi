from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware

from fastapi.staticfiles import StaticFiles
from core.database_2 import create_db_and_tables
from routers import auth, user, experience, education
from seed import seed


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(experience.router)
app.include_router(education.router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed()
