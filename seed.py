from sqlmodel import Session, select, SQLModel
from core.database_2 import engine
from schemas.User import User
from schemas.Experiences import Experience
from schemas.Education import Education
from datetime import datetime, date

from core.security import hash_password


def seed():
    with Session(engine) as session:
        # éviter de reseed si déjà rempli
        existing = session.exec(select(User)).first()
        if existing:
            print("Database already seeded")
            return

        for i in range(1, 11):
            # Calculer une date de naissance pour avoir environ 20+i ans
            birth_year = date.today().year - (20 + i)
            birth_date = date(birth_year, 1, 15)  # 15 janvier

            user = User(
                name=f"User{i}",
                first_name=f"Prénom{i}",
                birth_date=birth_date,
                mail=f"user{i}@mail.com",
                phone=f"06000000{i:02}",
                hashed_password=hash_password("test")

            )

            session.add(user)
            session.commit()
            session.refresh(user)

            # EDUCATION (1 par user)
            edu = Education(
                school_name=f"University {i}",
                date_start=datetime(2015, 9, 1),
                date_end=datetime(2019, 6, 1),
                description="Bachelor degree",
                major="Computer Science",
                user_id=user.id,
            )

            session.add(edu)

            # EXPERIENCES (2 par user)
            exp1 = Experience(
                title="Intern",
                date_start=datetime(2020, 1, 1),
                date_end=datetime(2020, 6, 1),
                description="First experience",
                company="Company A",
                user_id=user.id,
            )

            exp2 = Experience(
                title="Engineer",
                date_start=datetime(2021, 1, 1),
                date_end=datetime(2022, 1, 1),
                description="Second experience",
                company="Company B",
                user_id=user.id,
            )

            session.add(exp1)
            session.add(exp2)

        session.commit()
        print("Seeding complete")


def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("Database reset")


if __name__ == "__main__":
    reset_db()
    seed()
