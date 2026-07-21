"""Configure Alembic to migrate the database selected by the application.

Alembic imports this module for both migration execution and autogeneration.
Importing every table model populates ``SQLModel.metadata``, which is then used
to compare the declared schema with the connected database.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from core.database import engine
# These imports are intentionally unused as Python values: defining the classes
# registers their tables in SQLModel metadata for Alembic autogeneration.
from schemas.Education import Education  # noqa: F401
from schemas.Experiences import Experience  # noqa: F401
from schemas.Links import ExternalLink  # noqa: F401
from schemas.Projects import Project  # noqa: F401
from schemas.Skills import Skill  # noqa: F401
from schemas.User import User  # noqa: F401


# ``context.config`` represents the active ``alembic.ini`` plus any attributes
# injected by the application during startup.
config = context.config

if config.config_file_name is not None:
    # Reuse the loggers and formatter declared in alembic.ini when it is present.
    fileConfig(config.config_file_name)

# Autogenerate compares this metadata against the live database schema.
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Generate SQL without opening a live database connection.

    Literal values are embedded into the output because no DBAPI driver is
    available to bind parameters in offline mode.
    """
    # Alembic needs the complete URL internally to emit executable migration
    # configuration; callers must not print this value because it may contain a
    # database password.
    url = engine.url.render_as_string(hide_password=False)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection or a newly created one."""
    # Application startup supplies its existing transactional connection here;
    # direct ``alembic`` CLI commands leave the attribute unset.
    provided_connection = config.attributes.get("connection")

    if provided_connection is not None:
        context.configure(
            connection=provided_connection,
            target_metadata=target_metadata,
            compare_type=True,
            # Batch rendering provides SQLite-compatible table alterations.
            render_as_batch=provided_connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    # A direct CLI invocation builds a short-lived engine using the exact URL
    # resolved by core.database, rather than a duplicated value in alembic.ini.
    configuration = config.get_section(config.config_ini_section, {})
    # Preserve credentials for the DBAPI connection without logging this URL.
    configuration["sqlalchemy.url"] = engine.url.render_as_string(hide_password=False)
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # PostgreSQL supports ALTER operations directly; SQLite often needs
            # Alembic's copy-and-recreate batch strategy.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


# Alembic chooses offline mode for SQL script generation and online mode for
# applying or inspecting revisions against a database.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
