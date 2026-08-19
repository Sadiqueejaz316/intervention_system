"""Seed the development database with users to log in as.

DEVELOPMENT ONLY. The passwords below are published in the README so the team can
sign in during the hackathon; never run this against anything but a local database.

    python -m scripts.seed          # insert what is missing
    python -m scripts.seed --reset  # reset the seeded accounts' passwords too

Dispatchers and administrators exist only here: `/auth/register` deliberately
refuses those roles, so this script is the provisioning path for them.
"""

import argparse
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.enums import UserRole
from app.models.user import User

#: name, email, role, password, skills, latitude, longitude
SeedUser = tuple[str, str, UserRole, str, list[str], float | None, float | None]

SEED_USERS: list[SeedUser] = [
    (
        "Amina Admin",
        "admin@example.com",
        UserRole.ADMIN,
        "Admin123!",
        [],
        None,
        None,
    ),
    (
        "Dalia Dispatcher",
        "dispatcher@example.com",
        UserRole.DISPATCHER,
        "Dispatcher123!",
        [],
        None,
        None,
    ),
    (
        "Ahmed Contractor",
        "contractor1@example.com",
        UserRole.CONTRACTOR,
        "Contractor123!",
        ["ELECTRICAL", "MECHANICAL"],
        36.8065,
        10.1815,
    ),
    (
        "Bilal Contractor",
        "contractor2@example.com",
        UserRole.CONTRACTOR,
        "Contractor123!",
        ["PLUMBING", "GENERAL"],
        36.8500,
        10.2200,
    ),
    (
        "Rania Reporter",
        "reporter@example.com",
        UserRole.REPORTER,
        "Reporter123!",
        [],
        None,
        None,
    ),
]


def seed(db: Session, *, reset_passwords: bool) -> None:
    for name, email, role, password, skills, latitude, longitude in SEED_USERS:
        existing = db.execute(
            select(User).where(func.lower(User.email) == email)
        ).scalars().first()

        if existing is not None:
            if reset_passwords:
                existing.password_hash = hash_password(password)
                print(f"  reset password  {email}")
            else:
                print(f"  exists          {email}")
            continue

        db.add(
            User(
                name=name,
                email=email,
                role=role.value,
                password_hash=hash_password(password),
                skills=skills,
                latitude=latitude,
                longitude=longitude,
            )
        )
        print(f"  created         {email:28} {role.value}")

    db.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="reset the password of accounts that already exist",
    )
    args = parser.parse_args()

    if settings.ENVIRONMENT.lower() not in {"development", "local", "test"}:
        print(
            f"Refusing to seed: ENVIRONMENT is '{settings.ENVIRONMENT}'. "
            f"These are development-only credentials.",
            file=sys.stderr,
        )
        return 1

    print(f"Seeding {settings.DATABASE_URL.rsplit('/', 1)[-1]}")

    with SessionLocal() as db:
        seed(db, reset_passwords=args.reset)

    print("\nDevelopment credentials (never use these outside development):")
    for _, email, role, password, *_ in SEED_USERS:
        print(f"  {role.value:11} {email:28} {password}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
