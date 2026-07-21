# AGENTS.md

## Scope

These instructions apply to the entire repository.

## Project overview

This is a server-rendered e-portfolio application built with Python 3.12,
FastAPI, SQLModel, SQLite, Jinja2, and plain CSS. Keep the current architecture
simple: route handlers render HTML templates and process HTML form submissions;
this is not a JSON API or a JavaScript SPA.

Run all project commands from the repository root. The SQLite database,
`templates/`, and `static/` are referenced with paths relative to the current
working directory.

## Important files

- `main.py`: creates the FastAPI app, mounts static files, registers routers,
  creates tables, and runs the seed operation at startup.
- `routers/`: HTTP routes. Authentication and public discovery are in
  `auth.py`; user/profile routes are in `user.py`; owned CRUD is split between
  `experience.py` and `education.py`.
- `schemas/`: SQLModel table models. Preserve the existing case-sensitive file
  names and imports (`User.py`, `Experiences.py`, and `Education.py`).
- `core/database_2.py`: SQLite engine and per-request session dependency.
- `core/security.py`: password hashing and JWT creation/validation.
- `templates/`: Jinja2 pages and HTML forms.
- `static/`: page-specific and shared CSS.
- `seed.py`: idempotent sample-data seeding plus a destructive `reset_db()`
  helper.
- `database.db`: generated local state; it is intentionally ignored by Git.

## Setup and common commands

Create and activate a virtual environment, then install the pinned
dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a local `.env` containing a strong development secret:

```dotenv
SECRET_KEY=replace-with-a-long-random-value
```

Never commit `.env`, JWTs, passwords, password hashes, or `database.db`.

Start the development server:

```powershell
fastapi dev main.py
```

The application is available at `http://127.0.0.1:8000`. Startup creates the
SQLite tables and seeds sample users only when the user table is empty.

Useful Docker commands:

```powershell
docker compose config
docker build -f dockerfile -t e-portfolio .
```

Do not build an image from a workspace containing `.env` or `database.db` until
those files are excluded from the Docker build context. See the Docker safety
notes below.

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
- Before reading for edit, updating, or deleting an `Experience` or `Education`,
  verify that its `user_id` matches the authenticated user's `id`. Never trust a
  path ID or form value as proof of ownership.
- Hash new passwords with `hash_password`; never store or log plaintext
  passwords. Do not print tokens, secrets, cookie values, or full credentials.
- If cookie settings are changed, keep local development and production needs
  separate. Production authentication cookies should be secure, HTTP-only, and
  use an intentional SameSite policy.

## Database and seed safety

- The project currently has no migration framework. A model change does not
  automatically migrate an existing `database.db`; document the required
  migration or compatibility step instead of silently deleting data.
- Do not call `reset_db()` or remove `database.db` unless the user explicitly
  asks to reset local data.
- Keep seeding safe to run on every application startup. Do not make it overwrite
  or duplicate existing user data.
- Tests and experiments should use a temporary SQLite database or a dependency
  override rather than modifying a developer's real `database.db`.

## Verification

There is no automated test suite or configured linter yet. At minimum, verify
that the application and all registered routers import after a backend change.
The `-B` flag prevents this check from writing bytecode into existing cache
directories:

```powershell
python -B -c "from main import app; print(app.title)"
```

For route, template, or CSS changes, start the app and smoke-test the affected
flow in a browser. Depending on scope, check:

- `/`, search, pagination, and `/portfolio/{user_id}` as a signed-out visitor;
- registration, login, `/profil`, and logout;
- experience and education create, edit, and delete operations;
- attempts to edit or delete records belonging to another user;
- invalid or expired authentication cookies.

For Docker-related changes, run `docker compose config` and, when Docker is
available, build and start the service. Before finishing any task, inspect the
diff and ensure generated files, local data, and secrets are not included.

## Docker safety

- The Dockerfile is currently named lowercase `dockerfile`. Use
  `docker build -f dockerfile ...`, or explicitly fix the Compose configuration
  or filename before relying on builds on a case-sensitive host.
- The image uses `COPY . .`, while `.dockerignore` currently does not exclude
  `.env` or `database.db`. Never bake local secrets or data into an image; add
  the exclusions or use a clean build context before building.
- Compose bind-mounts `./database.db` at `/app/database.db`. Treat container
  startup and CRUD smoke tests as writes to the host database.

## Documentation and deployment

Update `README.md` when routes, setup steps, environment variables, dependency
requirements, or deployment behavior change. Production deploys from the
`prod-vm` branch via an automated Docker rebuild, so do not change deployment
scripts, branch assumptions, ports, or persistent-volume behavior without
calling out the operational impact.
