# AGENTS.md

## Scope

These instructions apply to the entire repository.

## Project overview

This is a server-rendered e-portfolio application built with Python 3.12,
FastAPI, SQLModel, Jinja2, and plain CSS. Docker Compose uses PostgreSQL 17 for
persistent data; SQLite remains the fallback for direct local runs and the
isolated test database. Keep the current architecture simple: route handlers
render HTML templates and process HTML form submissions; this is not a JSON API
or a JavaScript SPA.

Run all project commands from the repository root. Alembic configuration,
`templates/`, and `static/` are resolved relative to the repository.

## Important files

- `main.py`: creates the FastAPI app, installs CSRF middleware, mounts static
  files, registers routers, and runs migrations plus optional seeding during
  the application lifespan.
- `routers/`: HTTP routes. Authentication and public discovery are in
  `auth.py`; user/profile routes are in `user.py`; owned CRUD is split between
  `experience.py` and `education.py`.
- `schemas/`: SQLModel table models. Preserve the existing case-sensitive file
  names and imports (`User.py`, `Experiences.py`, and `Education.py`).
- `core/config.py`: validated environment settings and production-sensitive
  defaults for cookies and demonstration data.
- `core/database.py`: database URL selection, SQLModel engine, Alembic startup
  migration helper, and per-request session dependency. Resolution order is an
  explicit `DATABASE_URL`, Compose-style `POSTGRES_*` values, then SQLite.
- `core/authentication.py`: resolves the authenticated user from the JWT cookie.
- `core/csrf.py`: creates and validates double-submit CSRF tokens.
- `core/security.py`: password hashing and JWT creation/validation.
- `core/validation.py`: shared normalization and form-validation helpers.
- `migrations/`: Alembic environment and versioned schema migrations.
- `templates/`: Jinja2 pages and HTML forms.
- `static/`: page-specific and shared CSS.
- `seed.py`: idempotent sample-data seeding plus a destructive `reset_db()`
  helper.
- `tests/`: pytest unit and HTTP integration tests using isolated databases.
- `.github/workflows/ci.yml`: Python 3.12 dependency, import, migration, and
  test checks for pushes and pull requests.
- `docker-compose.yml`: local PostgreSQL, pgAdmin, and application services.
- `database.db`: optional SQLite fallback state; it is intentionally ignored by
  Git and is not used by Docker Compose.

## Setup and common commands

Create and activate a virtual environment, then install the pinned
dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy the environment template, then replace every placeholder secret:

```powershell
Copy-Item .env.example .env
```

For direct non-Docker development, `SECRET_KEY` is required and SQLite is used
when neither `DATABASE_URL` nor `POSTGRES_HOST` is configured. Docker Compose
also requires the PostgreSQL and pgAdmin values documented in `.env.example`.

Never commit `.env`, JWTs, passwords, password hashes, or `database.db`.

Start the development server:

```powershell
fastapi dev main.py
```

The application is available at `http://127.0.0.1:8000`. Startup upgrades the
configured database to the latest Alembic revision and synchronizes optional
demo data according to `APP_ENV` and `SEED_DEMO_DATA`.

Useful Docker commands:

```powershell
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs -f eportfolio
```

Compose reads secrets from the local `.env`; that file must remain untracked.
See the Docker safety notes below before deleting volumes or changing database
configuration.

## Implementation conventions

- Use four-space Python indentation, clear snake_case names, and type hints for
  new or changed functions. Keep imports grouped as standard library,
  third-party packages, then local modules.
- Keep route handlers and SQLModel database access synchronous unless a task
  deliberately converts the complete request path; do not mix in async database
  access piecemeal.
- Add routes to the router matching their domain. When adding a router module,
  also register it in `main.py`.
- Obtain database sessions through `Depends(get_session)` (or the existing
  `SessionDep` alias); do not create long-lived global sessions.
- After a successful form POST, return a `303` redirect so a browser refresh
  does not repeat the mutation.
- Keep HTML form `name` attributes synchronized with the route's `Form(...)`
  parameters. Create/edit templates share the `exp` and `edu` context values,
  so preserve both modes when changing them.
- Pass `request` to `TemplateResponse` and include it in template context where
  required by the existing Starlette/Jinja2 pattern.
- Keep styling in `static/*.css`. Preserve the current server-rendered approach
  unless a task explicitly calls for a frontend architecture change.
- Store `User.birth_date` as `date`. Experience and education dates are
  currently stored as `datetime` and parsed from form input with `%Y-%m-%d`.
- Use UTF-8 and preserve existing French and English copy. Avoid unrelated text,
  naming, or formatting rewrites.

## Authentication and data-ownership rules

- Protected routes read the `access_token` HTTP-only cookie, decode it, use the
  JWT `sub` claim as the user's email, and load that user from the database.
- Treat a missing, invalid, or expired token and a missing user as unauthenticated.
  Preserve the current redirect behavior unless a task changes the UX.
- Every state-changing HTML form route must validate the CSRF token submitted
  by the form against the HTTP-only CSRF cookie before applying the mutation.
- Normalize email addresses before account lookup or persistence so application
  checks remain aligned with the database uniqueness constraint.
- Before reading for edit, updating, or deleting an `Experience` or `Education`,
  verify that its `user_id` matches the authenticated user's `id`. Never trust a
  path ID or form value as proof of ownership.
- Hash new passwords with `hash_password`; never store or log plaintext
  passwords. Do not print tokens, secrets, cookie values, or full credentials.
- If cookie settings are changed, keep local development and production needs
  separate. Production authentication cookies should be secure, HTTP-only, and
  use an intentional SameSite policy.

## Database and seed safety

- Alembic is the migration framework. Any persisted model/schema change must
  include a reviewed migration under `migrations/versions/`; never rely on
  `SQLModel.metadata.create_all()` to evolve existing data.
- Never rewrite or delete an Alembic revision that may already have been
  applied. Create a new forward migration and review generated operations,
  especially PostgreSQL type conversions and constraints.
- Application startup calls `run_database_migrations()` before serving requests
  or synchronizing demo data. Verify new migrations with `upgrade`, `current`,
  and `check` against an isolated or explicitly selected database.
- `reset_db()` drops every table on the currently configured engine, including
  PostgreSQL. Do not call it or remove `database.db` unless the user explicitly
  asks to reset local data. Tests for destructive helpers must first replace the
  engine with a temporary SQLite engine.
- Docker data lives in the named `postgres_data` volume. Never use
  `docker compose down -v` unless the user explicitly requests deletion of the
  local PostgreSQL data.
- Keep seeding safe to run on every application startup. Do not make it overwrite
  or duplicate existing user data. Production seeding defaults to disabled.
- Tests and experiments should use a temporary SQLite database or a dependency
  override rather than modifying a developer's real SQLite or PostgreSQL data.

## Verification

The repository has an automated pytest suite with line and branch coverage.
`pytest.ini` enforces a minimum total coverage of 95%, and GitHub Actions runs
the suite on every push and pull request:

```powershell
python -m pytest
```

Use `--no-cov` only for a quick targeted test while developing; finish with the
complete command above so the configured coverage threshold is verified. Also
verify that the application and all registered routers import after backend or
startup changes. The `-B` flag avoids writing bytecode:

```powershell
python -B -c "from main import app; print(app.title)"
```

No linter is currently configured; do not claim lint verification unless a
linter is added and actually executed.

For route, template, or CSS changes, start the app and smoke-test the affected
flow in a browser. Depending on scope, check:

- `/`, search, pagination, and `/portfolio/{user_id}` as a signed-out visitor;
- registration, login, `/profil`, and logout;
- experience and education create, edit, and delete operations;
- attempts to edit or delete records belonging to another user;
- invalid or expired authentication cookies.

For migration changes, verify at minimum:

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

For Docker-related changes, run `docker compose config` and, when Docker is
available, build and start the affected service. Before finishing any task,
inspect the diff and ensure generated files, local data, coverage output, and
secrets are not included.

## Docker safety

- The Dockerfile is currently named lowercase `dockerfile`. Use
  `docker build -f dockerfile ...`; Compose already selects that filename
  explicitly, including on case-sensitive hosts.
- The image uses `COPY . .`. Keep `.dockerignore` exclusions for `.env`,
  `database.db`, virtual environments, Git metadata, and cache directories so
  local secrets and state never enter the image.
- Compose does not bind-mount application source or `database.db`. Rebuild the
  `eportfolio` image after code or dependency changes.
- PostgreSQL and pgAdmin persist through the named `postgres_data` and
  `pgadmin_data` volumes. Normal `docker compose down` preserves them.
- Local HTTP development should use `APP_ENV=development` and
  `COOKIE_SECURE=false`; production defaults require secure cookies.

## Documentation and deployment

Update `README.md` when routes, setup steps, environment variables, dependency
requirements, migrations, Docker behavior, or deployment behavior change.

There is currently no active production VM and no active automated deployment
target. Do not assume that `prod-vm` is deployed, run remote deployment actions,
or revive old branch/cron assumptions without an explicit user request and a
new deployment plan. Treat any older production-VM instructions in project
documentation as historical until they are deliberately replaced.
