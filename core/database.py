import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import URL
from sqlmodel import Session, SQLModel, create_engine


def get_database_url():
    """Return the configured database URL, with SQLite as a local fallback."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    postgres_host = os.getenv("POSTGRES_HOST")
    if postgres_host:
        return URL.create(
            drivername="postgresql+psycopg",
            username=os.getenv("POSTGRES_USER", "eportfolio"),
            password=os.getenv("POSTGRES_PASSWORD", "eportfolio_dev"),
            host=postgres_host,
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "eportfolio"),
        )

    return "sqlite:///database.db"


database_url = get_database_url()
engine_options = {"pool_pre_ping": True}

if str(database_url).startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(database_url, **engine_options)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_db_and_tables() -> None:
    """Create tables for legacy callers; application startup uses Alembic."""
    SQLModel.metadata.create_all(engine)


def run_database_migrations() -> None:
    """Upgrade the configured database to the latest Alembic revision."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
