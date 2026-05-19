# Yassine Gharbi & Guillaume de Montgolfier — e-portfolio

## Live Demo

Deployed application:

https://k2vm-229.mde.epf.fr/

---

## Overview

This project is a web application built with FastAPI to manage a personal e-portfolio.

It allows users to:
- create an account
- securely log in
- manage their personal profile
- add, edit, and delete professional experiences
- add, edit, and delete education entries
- public portfolio pages accessible to everyone
- a public homepage listing e-portfolios
- portfolio search functionality

---

## Tech Stack

- Language: Python
- Framework: FastAPI
- Database: SQLite (via SQLModel)
- Authentication: JWT + HTTP-only cookies
- Password hashing: pwdlib / Argon2
- Templating: Jinja2
- Frontend: HTML + CSS

---

## Features

### Public Portfolio System
- Public e-portfolio pages
- Public homepage listing users
- Portfolio search system
- Public/private route separation

### Authentication & Security
- Secure login/logout system
- JWT authentication
- HTTP-only authentication cookies
- Password hashing using Argon2
- Protected routes
- User session invalidation after logout

### User Features
- User creation with database persistence
- Dynamic profile page
- Automatic age calculation from birth date

### CRUD Operations
- Experiences
  - Create
  - Read
  - Update
  - Delete

- Educations
  - Create
  - Read
  - Update
  - Delete

### Multi-user Support
- Each user has their own experiences and educations
- Relational ownership system
- Data isolation between users
- Users cannot edit another user's data

---

## Main Routes

| Route | Description |
|---|---|
| `/` | Public homepage |
| `/login` | Login page |
| `/profil` | Private user dashboard |
| `/portfolio/{id}` | Public portfolio page |

## Database Design

The application uses a relational database with SQLModel.

### User
- id (PK)
- name
- first_name
- birth_date
- mail
- phone
- hashed_password

### Experience
- id (PK)
- title
- company
- date_start
- date_end
- description
- user_id (FK → User.id)

### Education
- id (PK)
- school_name
- major
- date_start
- date_end
- description
- user_id (FK → User.id)

---

## Relationships

### User → Experience : 1 → N
One user can own multiple experiences.

### User → Education : 1 → N
One user can own multiple education entries.

This means:
- each experience belongs to one user
- each education entry belongs to one user

---

## Project Structure

```text
├── core/           # Database & security logic
├── routers/        # FastAPI route handlers
├── schemas/        # SQLModel database models
├── templates/      # Jinja2 HTML templates
├── static/         # CSS files
├── seed.py         # Database seeding
├── main.py         # Application entry point
````

---

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv env
source env/bin/activate   # Linux / Mac
env\Scripts\activate      # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
fastapi dev
```

Then open:

```text
http://127.0.0.1:8000
```

---

## Notes

* The database is automatically created at startup
* The database can be automatically seeded with demo users
* If models are modified, the SQLite database may need to be recreated
* Authentication is handled with JWT tokens stored in HTTP-only cookies
* Passwords are securely hashed before storage

---

## Docker Containerization

### 1. Build docker image 

```bash
docker build -t eportfolio-app .
```

### 2. Lancer le conteneur

```bash
docker run -p 8000:8000 eportfolio-app
```

### 3. Ou utiliser docker-compose

```bash
docker-compose up --build
```

L'application sera alors accessible sur :

```
http://localhost:8000
```

### 4. Arrêter les conteneurs

```bash
docker-compose down
```

---

**Remarques :**
- Le fichier `docker-compose.yml` monte le fichier `database.db` pour persister les données.
- Le fichier `.dockerignore` exclut les fichiers/dossiers inutiles du build Docker.
- Le port 8000 est exposé par défaut.

