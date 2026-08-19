"""Registration, login and token validation."""

from datetime import timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, verify_password
from app.core.enums import UserRole
from app.models.user import User
from tests.conftest import TEST_PASSWORD, auth, make_user


def _registration(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Ahmed Newcomer",
        "email": "ahmed.newcomer@example.com",
        "password": "password123",
        "role": "CONTRACTOR",
    }
    payload.update(overrides)

    return payload


def test_register_creates_a_user_with_a_hashed_password(
    client: TestClient,
    db: Session,
) -> None:
    response = client.post("/auth/register", json=_registration())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ahmed.newcomer@example.com"
    assert body["role"] == "CONTRACTOR"
    assert "password" not in body
    assert "password_hash" not in body

    stored = db.execute(
        select(User).where(User.email == "ahmed.newcomer@example.com")
    ).scalars().one()
    assert stored.password_hash != "password123"
    assert verify_password("password123", stored.password_hash)


def test_registered_user_can_log_in(client: TestClient) -> None:
    client.post("/auth/register", json=_registration())

    response = client.post(
        "/auth/login",
        json={"email": "ahmed.newcomer@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_register_rejects_a_duplicate_email(client: TestClient) -> None:
    client.post("/auth/register", json=_registration())

    response = client.post("/auth/register", json=_registration(name="Someone Else"))

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_refuses_privileged_roles(client: TestClient) -> None:
    """Nobody grants themselves dispatch or full access; those come from seeding."""
    for role in ("ADMIN", "DISPATCHER"):
        response = client.post("/auth/register", json=_registration(role=role))

        assert response.status_code == 422
        assert "administrator" in response.json()["detail"]


def test_register_rejects_a_short_password(client: TestClient) -> None:
    response = client.post("/auth/register", json=_registration(password="short"))

    assert response.status_code == 422


def test_login_returns_a_usable_token(client: TestClient, reporter: User) -> None:
    response = client.post(
        "/auth/login",
        json={"email": reporter.email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["id"] == str(reporter.id)


def test_login_with_the_wrong_password_is_rejected(
    client: TestClient,
    reporter: User,
) -> None:
    response = client.post(
        "/auth/login",
        json={"email": reporter.email, "password": "not-my-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_login_with_an_unknown_email_gives_the_same_answer(
    client: TestClient,
    reporter: User,
) -> None:
    """A wrong address and a wrong password must be indistinguishable."""
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_login_ignores_email_casing(client: TestClient, reporter: User) -> None:
    response = client.post(
        "/auth/login",
        json={"email": reporter.email.upper(), "password": TEST_PASSWORD},
    )

    assert response.status_code == 200


def test_login_form_flow_works_for_the_docs_authorize_button(
    client: TestClient,
    dispatcher: User,
) -> None:
    response = client.post(
        "/auth/token",
        data={"username": dispatcher.email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_an_account_without_a_password_cannot_log_in(
    client: TestClient,
    db: Session,
) -> None:
    """Imported or seeded rows may have no hash; they must simply not sign in."""
    legacy = make_user(
        db,
        name="Legacy Worker",
        role=UserRole.CONTRACTOR,
        password_hash=None,
    )

    response = client.post(
        "/auth/login",
        json={"email": legacy.email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 401


def test_me_returns_the_signed_in_user_without_the_hash(
    client: TestClient,
    contractor: User,
) -> None:
    response = client.get("/auth/me", headers=auth(contractor))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == contractor.email
    assert body["role"] == "CONTRACTOR"
    assert "password_hash" not in body


def test_me_without_a_token_is_unauthorized(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_a_malformed_token_is_unauthorized(client: TestClient) -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_a_token_signed_with_another_key_is_unauthorized(
    client: TestClient,
    reporter: User,
) -> None:
    forged = jwt.encode({"sub": str(reporter.id)}, "attacker-key", algorithm="HS256")

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401


def test_an_expired_token_is_unauthorized(client: TestClient, reporter: User) -> None:
    expired = create_access_token(
        user_id=reporter.id,
        role=reporter.role,
        expires_delta=timedelta(minutes=-1),
    )

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


def test_a_token_for_a_deleted_user_is_unauthorized(client: TestClient) -> None:
    token = create_access_token(user_id=uuid4(), role=UserRole.ADMIN)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_the_database_role_wins_over_the_token_claim(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    """A token claiming DISPATCHER gets a reporter nowhere: the role is re-read."""
    ticket = client.post(
        "/tickets",
        json={"title": "Street light out", "type": "OUTAGE"},
        headers=auth(reporter),
    ).json()

    inflated = create_access_token(user_id=reporter.id, role=UserRole.DISPATCHER)

    response = client.post(
        f"/tickets/{ticket['id']}/assign",
        json={"contractor_id": str(contractor.id)},
        headers={"Authorization": f"Bearer {inflated}"},
    )

    assert response.status_code == 403
