"""Unit tests for database URL selection and lifecycle helpers."""

from __future__ import annotations

from runpy import run_path
from unittest.mock import MagicMock

import pytest
import sqlmodel
from alembic import command
from alembic import config as alembic_config
from sqlalchemy import URL

from core import database as database_module


POSTGRES_ENVIRONMENT_VARIABLES = (
    "POSTGRES_HOST",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_PORT",
    "POSTGRES_DB",
)


def clear_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove database selectors without changing the process permanently."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for variable_name in POSTGRES_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)


def test_explicit_database_url_has_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    explicit_url = "sqlite:////tmp/explicit-test.db"
    monkeypatch.setenv("DATABASE_URL", explicit_url)
    monkeypatch.setenv("POSTGRES_HOST", "ignored-database-host")

    assert database_module.get_database_url() == explicit_url


def test_postgres_url_uses_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_database_environment(monkeypatch)
    monkeypatch.setenv("POSTGRES_HOST", "postgres")

    database_url = database_module.get_database_url()

    assert isinstance(database_url, URL)
    assert database_url.drivername == "postgresql+psycopg"
    assert database_url.username == "eportfolio"
    assert database_url.password == "eportfolio_dev"
    assert database_url.host == "postgres"
    assert database_url.port == 5432
    assert database_url.database == "eportfolio"


def test_postgres_url_uses_custom_values_and_escapes_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_database_environment(monkeypatch)
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("POSTGRES_USER", "portfolio_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss/word:#?")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv("POSTGRES_DB", "portfolio")

    database_url = database_module.get_database_url()

    assert isinstance(database_url, URL)
    assert database_url.username == "portfolio_user"
    assert database_url.password == "p@ss/word:#?"
    assert database_url.host == "db.internal"
    assert database_url.port == 6543
    assert database_url.database == "portfolio"
    assert database_url.render_as_string(hide_password=False) == (
        "postgresql+psycopg://portfolio_user:"
        "p%40ss%2Fword%3A%23%3F@db.internal:6543/portfolio"
    )


def test_database_url_falls_back_to_local_sqlite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_database_environment(monkeypatch)

    assert database_module.get_database_url() == "sqlite:///database.db"


def test_postgres_engine_does_not_receive_sqlite_thread_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise module initialization without opening a database connection."""
    clear_database_environment(monkeypatch)
    monkeypatch.setenv("POSTGRES_HOST", "postgres")
    fake_engine = object()
    create_engine = MagicMock(return_value=fake_engine)
    monkeypatch.setattr(sqlmodel, "create_engine", create_engine)

    module_globals = run_path(
        str(database_module.PROJECT_ROOT / "core" / "database.py"),
        run_name="database_postgres_initialization_test",
    )

    configured_url = create_engine.call_args.args[0]
    assert isinstance(configured_url, URL)
    assert configured_url.host == "postgres"
    create_engine.assert_called_once_with(configured_url, pool_pre_ping=True)
    assert module_globals["engine"] is fake_engine


def test_run_database_migrations_injects_managed_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = object()
    begin_context = MagicMock()
    begin_context.__enter__.return_value = connection
    fake_engine = MagicMock()
    fake_engine.begin.return_value = begin_context

    config = MagicMock()
    config.attributes = {}
    config_factory = MagicMock(return_value=config)
    upgrade = MagicMock()

    monkeypatch.setattr(database_module, "engine", fake_engine)
    monkeypatch.setattr(alembic_config, "Config", config_factory)
    monkeypatch.setattr(command, "upgrade", upgrade)

    database_module.run_database_migrations()

    config_factory.assert_called_once_with(
        str(database_module.PROJECT_ROOT / "alembic.ini")
    )
    fake_engine.begin.assert_called_once_with()
    assert config.attributes["connection"] is connection
    upgrade.assert_called_once_with(config, "head")
    begin_context.__exit__.assert_called_once()


def test_get_session_yields_and_closes_request_scoped_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = object()
    session_context = MagicMock()
    session_context.__enter__.return_value = session
    session_factory = MagicMock(return_value=session_context)
    monkeypatch.setattr(database_module, "Session", session_factory)

    session_generator = database_module.get_session()

    assert next(session_generator) is session
    with pytest.raises(StopIteration):
        next(session_generator)

    session_factory.assert_called_once_with(database_module.engine)
    session_context.__exit__.assert_called_once_with(None, None, None)
