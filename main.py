from fastapi import FastAPI


from fastapi.staticfiles import StaticFiles
from core.database_2 import create_db_and_tables
from routers import auth, user, experience, education
from seed import seed


app = FastAPI()

# mount static files for css
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(experience.router)
app.include_router(education.router)

"""
#it's better to use lifespan bc it's more recent
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed()

"""


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed()
