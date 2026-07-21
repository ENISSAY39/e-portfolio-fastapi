"""Configure the database engine, migrations, and request-scoped sessions."""

import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import URL
from sqlmodel import Session, create_engine


def get_database_url():
    """Return the configured database URL, with SQLite as a local fallback.

    A complete ``DATABASE_URL`` has highest priority. Compose-style PostgreSQL
    components are assembled only when ``POSTGRES_HOST`` is set, allowing the
    same application image to connect to the database service by hostname.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    postgres_host = os.getenv("POSTGRES_HOST")
    if postgres_host:
        # URL.create performs correct credential escaping and avoids manually
        # concatenating passwords that may contain reserved URL characters.
        return URL.create(
            drivername="postgresql+psycopg",
            username=os.getenv("POSTGRES_USER", "eportfolio"),
            password=os.getenv("POSTGRES_PASSWORD", "eportfolio_dev"),
            host=postgres_host,
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "eportfolio"),
        )

    # SQLite keeps a zero-configuration local fallback for non-Compose tooling.
    return "sqlite:///database.db"


database_url = get_database_url()
# Detect stale pooled connections before handing them to an HTTP request.
engine_options = {"pool_pre_ping": True}

if str(database_url).startswith("sqlite"):
    # FastAPI may serve requests on different threads, so the default SQLite
    # same-thread guard is incompatible with the shared engine.
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(database_url, **engine_options)

# Resolve Alembic configuration from the repository root even if this module is
# imported after a caller changes the process working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_database_migrations() -> None:
    """Upgrade the configured database to the latest Alembic revision.

    The already configured application engine is injected into Alembic so
    startup cannot accidentally migrate a different database URL.
    """
    # Keep Alembic imports local: regular session consumers do not need to load
    # migration tooling merely by importing this database module.
    from alembic import command
    from alembic.config import Config

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    with engine.begin() as connection:
        # ``env.py`` detects this connection and avoids constructing a second
        # engine, keeping the upgrade within this managed transaction context.
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def get_session():
    """Yield one SQLModel session and close it after the request completes."""
    with Session(engine) as session:
        yield session


# Route annotations can use this alias to obtain the request-scoped dependency
# without repeating ``Depends(get_session)`` in every handler signature.
SessionDep = Annotated[Session, Depends(get_session)]
