from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.schemas import SELF_REGISTERABLE_ROLES, RegisterRequest
from app.auth.security import burn_password_check, hash_password, verify_password
from app.core.errors import ConflictError, DomainValidationError
from app.models.user import User


def register(db: Session, data: RegisterRequest) -> User:
    if data.role not in SELF_REGISTERABLE_ROLES:
        raise DomainValidationError(
            f"{data.role} accounts are provisioned by an administrator. "
            f"Register as one of: "
            f"{', '.join(role.value for role in SELF_REGISTERABLE_ROLES)}."
        )

    email = data.email.lower()
    if get_by_email(db, email) is not None:
        raise ConflictError("An account with this email already exists.")

    user = User(
        name=data.name,
        email=email,
        role=data.role.value,
        password_hash=hash_password(data.password),
        skills=[skill.upper() for skill in data.skills],
        latitude=data.latitude,
        longitude=data.longitude,
    )

    try:
        db.add(user)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(user)

    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    """The user if the credentials match, otherwise None.

    Callers must not distinguish "no such account" from "wrong password" in what
    they return to the client.
    """
    user = get_by_email(db, email.lower())
    if user is None:
        burn_password_check(password)
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def get_by_email(db: Session, email: str) -> User | None:
    query = select(User).where(func.lower(User.email) == email.lower())

    return db.execute(query).scalars().first()
