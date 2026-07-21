from datetime import datetime, date

from sqlmodel import Session, SQLModel, select

from core.database import engine
from core.security import hash_password
from schemas.Education import Education
from schemas.Experiences import Experience
from schemas.User import User


def seed():
    with Session(engine) as session:
        created_users = 0
        created_educations = 0
        created_experiences = 0
        seed_password_hash = None

        for i in range(1, 11):
            mail = f"user{i}@mail.com"
            birth_year = date.today().year - (20 + i)
            user = session.exec(select(User).where(User.mail == mail)).first()

            if user is None:
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
                session.flush()
                created_users += 1

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

        session.commit()
        print(
            "Seed synchronized: "
            f"{created_users} user(s), "
            f"{created_educations} education(s), "
            f"{created_experiences} experience(s) created"
        )


def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("Database reset")


"""
if __name__ == "__main__":
    reset_db()
    seed()
"""
