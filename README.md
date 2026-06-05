# Yassine Gharbi & Guillaume de Montgolfier — e-Portfolio

## Live Demo

Deployed application:

https://k2vm-229.mde.epf.fr/

---

## Overview

This project is a web application built with FastAPI that allows users to create and manage a personal e-portfolio.

The platform provides both public and private features:

* User registration
* Secure authentication
* Personal profile management
* Experience management
* Education management
* Public portfolio publication
* Portfolio search system
* Portfolio pagination system

The application follows a classic web architecture with a FastAPI backend, Jinja2 templates for rendering, and SQLite for data persistence.

---

## Tech Stack

### Backend

* Python 3.12
* FastAPI
* SQLModel
* SQLite

### Security

* JWT Authentication
* HTTP-only Cookies
* Argon2 Password Hashing

### Frontend

* HTML
* CSS
* Jinja2 Templates

### DevOps

* Docker
* Docker Compose
* Git
* Cron-based Continuous Deployment

---

## Features

### Public Features

* Public homepage listing all available portfolios
* Search portfolios by name
* Pagination system
* Public portfolio pages accessible without authentication

### Authentication & Security

* User registration
* Secure login/logout
* JWT-based authentication
* HTTP-only authentication cookies
* Password hashing using Argon2
* Protected routes
* Session invalidation after logout

### Profile Management

* Personal profile page
* Automatic age calculation from birth date
* Display personal information

### Experience Management

* Create experiences
* Read experiences
* Update experiences
* Delete experiences

### Education Management

* Create education entries
* Read education entries
* Update education entries
* Delete education entries

### Multi-user Support

* Data ownership system
* User isolation
* Protected user resources
* Users cannot modify another user's data

---

## Application Routes

| Route             | Description       |
| ----------------- | ----------------- |
| `/`               | Public homepage   |
| `/search`         | Portfolio search  |
| `/login`          | Login page        |
| `/create_user`    | User registration |
| `/profil`         | Private dashboard |
| `/portfolio/{id}` | Public portfolio  |

---

## Database Design

The application uses a relational database implemented with SQLModel.

### User

| Field           | Type        |
| --------------- | ----------- |
| id              | Primary Key |
| name            | String      |
| first_name      | String      |
| birth_date      | Date        |
| mail            | String      |
| phone           | String      |
| hashed_password | String      |

### Experience

| Field       | Type        |
| ----------- | ----------- |
| id          | Primary Key |
| title       | String      |
| company     | String      |
| date_start  | Date        |
| date_end    | Date        |
| description | String      |
| user_id     | Foreign Key |

### Education

| Field       | Type        |
| ----------- | ----------- |
| id          | Primary Key |
| school_name | String      |
| major       | String      |
| date_start  | Date        |
| date_end    | Date        |
| description | String      |
| user_id     | Foreign Key |

---

## Relationships

### User → Experience (1:N)

A user can own multiple professional experiences.

### User → Education (1:N)

A user can own multiple education entries.

Relationship rules:

* One experience belongs to one user.
* One education entry belongs to one user.
* Deleting a user removes access to their associated records.

---

## Project Structure

```text
.
├── core/
│   ├── database_2.py
│   └── security.py
│
├── routers/
│   ├── auth.py
│   ├── education.py
│   └── experience.py
│   └── user.py
    


│
├── schemas/
│   ├── User.py
│   ├── Experience.py
│   └── Education.py
│
├── static/
│   ├── base.css
│   ├── home.css
│   ├── login_style.css
│   ├── create_user.css
│   └── public_profile.css
│   └── login.css


│
├── templates/
│   ├── home.html
│   ├── login.html
│   ├── profil.html
│   ├── experience.html
│   ├── education.html
│   └── public_profile.html
│   └── create_user.html

│
├── docker-compose.yml
├── dockerfile
├── requirements.txt
├── seed.py
└── main.py
```

---

## Local Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd e-portfolio
```

### 2. Create a Virtual Environment

```bash
python3 -m venv env
source env/bin/activate
```

Windows:

```bash
env\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```
## Dependencies

This section explains the key dependencies and why they were chosen.

### Core Framework

| Package | Role |
|---|---|
| `fastapi` | Web framework — chosen for its automatic OpenAPI docs, native Pydantic integration, and async support |
| `uvicorn` | ASGI server used to run the FastAPI app in production |
| `starlette` | Underlying toolkit FastAPI is built on (routing, middleware, static files) |
| `jinja2` | HTML templating engine for server-side rendering |
| `python-multipart` | Required to handle HTML form submissions (login, registration) |

### Database

| Package | Role |
|---|---|
| `sqlmodel` | ORM chosen for its dual role: defines models used both as database tables and as Pydantic validation schemas, avoiding code duplication |
| `sqlalchemy` | Underlying database engine used by SQLModel |
| `greenlet` | Required by SQLAlchemy for async context support |

### Security

| Package | Role |
|---|---|
| `argon2-cffi` | Argon2 password hashing — chosen over bcrypt or SHA-256 for its resistance to GPU and ASIC brute-force attacks (memory-hard algorithm) |
| `pwdlib` | High-level wrapper around argon2-cffi for password hashing/verification |
| `pyjwt` | JWT token generation and verification for stateless authentication |
| `python-dotenv` | Loads environment variables (secret key, config) from a `.env` file |

### Validation

| Package | Role |
|---|---|
| `pydantic` | Data validation library, used natively by FastAPI for request/response schemas |
| `annotated-types` | Extends Python type annotations, used internally by Pydantic |

### Dev & CLI

| Package | Role |
|---|---|
| `fastapi-cli` | Provides the `fastapi run` and `fastapi dev` commands |
| `click`, `typer`, `rich` | CLI utilities used internally by fastapi-cli |
| `watchfiles` | File watching for hot-reload in development mode |

> **Note:** Some packages in `requirements.txt` are transitive dependencies (automatically installed by the packages above) and are not imported directly in the application code.

### 4. Start the Application

```bash
fastapi dev
```

Application available at:

```text
http://127.0.0.1:8000
```

---

## Docker Deployment

### Build Image

```bash
docker build -t e-portfolio .
```

### Start Container

```bash
docker compose up -d
```

### Rebuild Container

```bash
docker compose up -d --build
```

---

## Automated Deployment

The production environment uses an automated deployment strategy directly executed on the virtual machine.

Every 2 minutes, a deployment script checks the `prod-vm` branch and automatically deploys any new version.

### Deployment Script

```bash
#!/bin/bash

echo "DEPLOY $(date)"

cd /home/yassine/web_prog/e-portfolio || exit 1

git pull origin prod-vm

sudo docker compose up -d --build

sudo docker image prune -f

echo "DEPLOY DONE $(date)"
```

### Cron Configuration

```cron
*/2 * * * * /home/yassine/deploy.sh >> /home/yassine/deploy.log 2>&1
```

### Deployment Workflow

1. Fetch latest code from GitHub.
2. Pull updates from the `prod-vm` branch.
3. Rebuild Docker image.
4. Recreate application container.
5. Remove unused Docker images.
6. Store deployment logs.

### Deployment Logs

```text
/home/yassine/deploy.log
```

### Benefits

* Fully automated deployment.
* No manual intervention required.
* No public SSH exposure.
* Compatible with Proxmox and NAT environments.
* Automatic Docker image cleanup.
* Continuous synchronization with the production branch.

---

## Notes

* The SQLite database is automatically created on startup.
* Authentication relies on JWT tokens stored in HTTP-only cookies.
* Passwords are hashed before storage using Argon2.
* Pagination is implemented on the public homepage and search results.
* Docker is used for production deployment.
