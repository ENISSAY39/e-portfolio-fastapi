"""Synchronize optional demonstration records with the configured database.

The seed operation is intentionally idempotent: it looks up every demonstration
record by stable identifying fields before inserting it. Production startup
disables this module by default through :mod:`core.config`.
"""

from datetime import datetime, date

from sqlmodel import Session, SQLModel, select

from core.database import engine
from core.security import hash_password
from schemas.Education import Education
from schemas.Experiences import Experience
from schemas.User import User


def seed():
    """Insert any missing demo users, education entries, and experiences.

    Existing rows are preserved and no plaintext password is stored. A single
    password hash is reused for newly created demo users during this run because
    password hashing is intentionally computationally expensive.
    """
    with Session(engine) as session:
        # Counters make the startup log useful without exposing record contents.
        created_users = 0
        created_educations = 0
        created_experiences = 0
        seed_password_hash = None

        for i in range(1, 11):
            # Email acts as the stable identity for each demonstration user.
            mail = f"user{i}@mail.com"
            birth_year = date.today().year - (20 + i)
            user = session.exec(select(User).where(User.mail == mail)).first()

            if user is None:
                # Compute the deliberately shared demo password only if at least
                # one user needs to be created; production seeding stays off.
                if seed_password_hash is None:
                    seed_password_hash = hash_password("test")

                user = User(
                    name=f"User{i}",
                    first_name=f"Prénom{i}",
                    birth_date=date(birth_year, 1, 15),
                    mail=mail,
                    phone=f"06000000{i:02}",
                    hashed_password=seed_password_hash,
                )
                session.add(user)
                # Obtain the database-generated user ID before creating rows
                # that reference it through a foreign key.
                session.flush()
                created_users += 1

            # School name and owner together identify the single demo education
            # row, allowing repeated startups without creating duplicates.
            education = session.exec(
                select(Education).where(
                    Education.user_id == user.id,
                    Education.school_name == f"University {i}",
                )
            ).first()
            if education is None:
                session.add(
                    Education(
                        school_name=f"University {i}",
                        date_start=datetime(2015, 9, 1),
                        date_end=datetime(2019, 6, 1),
                        description="Bachelor degree",
                        major="Computer Science",
                        user_id=user.id,
                    )
                )
                created_educations += 1

            # Keep the intended sample timeline close to the synchronization
            # loop so each tuple can be unpacked into an Experience unchanged.
            experiences = (
                (
                    "Intern",
                    datetime(2020, 1, 1),
                    datetime(2020, 6, 1),
                    "First experience",
                    "Company A",
                ),
                (
                    "Engineer",
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                    "Second experience",
                    "Company B",
                ),
            )

            for title, date_start, date_end, description, company in experiences:
                # A title/company/owner combination is stable enough for this
                # fixed demo dataset and does not affect real user records.
                experience = session.exec(
                    select(Experience).where(
                        Experience.user_id == user.id,
                        Experience.title == title,
                        Experience.company == company,
                    )
                ).first()
                if experience is None:
                    session.add(
                        Experience(
                            title=title,
                            date_start=date_start,
                            date_end=date_end,
                            description=description,
                            company=company,
                            user_id=user.id,
                        )
                    )
                    created_experiences += 1

        # Commit all inserted demo rows atomically after the full synchronization.
        session.commit()
        print(
            "Seed synchronized: "
            f"{created_users} user(s), "
            f"{created_educations} education(s), "
            f"{created_experiences} experience(s) created"
        )


def reset_db():
    """Destructively recreate every SQLModel table in the configured database.

    This helper is kept for deliberate local maintenance only and is never
    called by application startup. Calling it permanently deletes stored data.
    """
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("Database reset")


# The manual reset/seed entry point remains disabled to prevent an accidental
# ``python seed.py`` invocation from deleting a developer's database.
"""
if __name__ == "__main__":
    reset_db()
    seed()
"""
