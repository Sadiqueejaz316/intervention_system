from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.auth.security import create_access_token, hash_password
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.enums import UserRole
from app.main import app
from app.models.user import User

CORE_TABLES = "notifications, ticket_history, assignments, tickets, users"

#: Password every fixture user signs in with.
TEST_PASSWORD = "Password123!"

# Argon2 is deliberately slow, so the suite hashes the shared password once
# instead of once per fixture user.
_TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


def _create_test_database_if_missing() -> None:
    url = make_url(settings.TEST_DATABASE_URL)
    admin_engine = create_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )

    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        ).scalar()

        if not exists:
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))

    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine() -> Generator[Engine]:
    _create_test_database_if_missing()

    test_engine = create_engine(settings.TEST_DATABASE_URL)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)

    yield test_engine

    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Generator[Session]:
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        with engine.begin() as connection:
            connection.execute(
                text(f"TRUNCATE {CORE_TABLES} RESTART IDENTITY CASCADE")
            )


def make_user(
    db: Session,
    *,
    name: str,
    role: UserRole,
    skills: list[str] | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    is_available: bool = True,
    password_hash: str | None = _TEST_PASSWORD_HASH,
) -> User:
    user = User(
        name=name,
        email=f"{name.lower().replace(' ', '.')}@example.com",
        role=role.value,
        password_hash=password_hash,
        skills=skills or [],
        latitude=latitude,
        longitude=longitude,
        is_available=is_available,
    )
    db.add(user)
    db.commit()

    return user


def auth(user: User) -> dict[str, str]:
    """Authorization header for `user`.

    Tokens are minted directly rather than through `/auth/login` so that the
    password hash is verified once per suite; `tests/test_auth.py` exercises the
    real login exchange.
    """
    token = create_access_token(user_id=user.id, role=user.role)

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def reporter(db: Session) -> User:
    return make_user(db, name="Rania Reporter", role=UserRole.REPORTER)


@pytest.fixture
def dispatcher(db: Session) -> User:
    return make_user(db, name="Dalia Dispatcher", role=UserRole.DISPATCHER)


@pytest.fixture
def contractor(db: Session) -> User:
    return make_user(
        db,
        name="Ahmed Contractor",
        role=UserRole.CONTRACTOR,
        skills=["ELECTRICAL", "MECHANICAL"],
        latitude=36.81,
        longitude=10.19,
    )


@pytest.fixture
def admin(db: Session) -> User:
    return make_user(db, name="Amina Admin", role=UserRole.ADMIN)


@pytest.fixture
def client(db: Session) -> Generator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
