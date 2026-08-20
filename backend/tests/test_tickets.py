from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket_history import TicketHistory
from app.models.user import User
from tests.conftest import auth


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Landing doors stuck on ELV-02",
        "description": "Doors reverse on every close attempt.",
        "type": "DOOR_MALFUNCTION",
        "priority": "CRITICAL",
        "location_text": "Building A, ELV-02",
        "latitude": 36.8065,
        "longitude": 10.1815,
        "metadata": {"building_name": "Building A", "elevator_id": "ELV-02"},
    }
    payload.update(overrides)

    return payload


def test_create_ticket_starts_open(client: TestClient, reporter: User) -> None:
    response = client.post("/tickets", json=_payload(), headers=auth(reporter))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "OPEN"
    assert body["priority"] == "CRITICAL"
    assert body["metadata"]["elevator_id"] == "ELV-02"


def test_create_ticket_records_the_authenticated_reporter(
    client: TestClient,
    reporter: User,
) -> None:
    """The reporter comes from the token; the client cannot name someone else."""
    response = client.post(
        "/tickets",
        json=_payload(reporter_id=str(uuid4())),
        headers=auth(reporter),
    )

    assert response.status_code == 201
    assert response.json()["reporter_id"] == str(reporter.id)


def test_create_ticket_rejects_unknown_issue_type(
    client: TestClient,
    reporter: User,
) -> None:
    response = client.post(
        "/tickets",
        json=_payload(type="SPACESHIP"),
        headers=auth(reporter),
    )

    assert response.status_code == 422
    assert "SPACESHIP" in response.json()["detail"]


def test_get_ticket_returns_created_ticket(client: TestClient, reporter: User) -> None:
    created = client.post("/tickets", json=_payload(), headers=auth(reporter)).json()

    response = client.get(f"/tickets/{created['id']}", headers=auth(reporter))

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_unknown_ticket_returns_404(client: TestClient, dispatcher: User) -> None:
    response = client.get(f"/tickets/{uuid4()}", headers=auth(dispatcher))

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_ticket_creation_writes_history(
    client: TestClient,
    db: Session,
    reporter: User,
) -> None:
    created = client.post("/tickets", json=_payload(), headers=auth(reporter)).json()

    entries = db.execute(
        select(TicketHistory).where(TicketHistory.ticket_id == created["id"])
    ).scalars().all()

    assert len(entries) == 1
    assert entries[0].action == "TICKET_CREATED"
    assert entries[0].new_status == "OPEN"
    assert entries[0].user_id == reporter.id


def test_list_tickets_puts_critical_first(
    client: TestClient,
    reporter: User,
    dispatcher: User,
) -> None:
    client.post(
        "/tickets",
        json=_payload(title="Low priority job", priority="LOW"),
        headers=auth(reporter),
    )
    client.post(
        "/tickets",
        json=_payload(title="Urgent job", priority="CRITICAL"),
        headers=auth(reporter),
    )

    response = client.get("/tickets", headers=auth(dispatcher))

    assert response.status_code == 200
    titles = [ticket["title"] for ticket in response.json()]
    assert titles == ["Urgent job", "Low priority job"]


def test_list_tickets_filters_by_priority(
    client: TestClient,
    reporter: User,
    dispatcher: User,
) -> None:
    client.post("/tickets", json=_payload(priority="LOW"), headers=auth(reporter))
    client.post("/tickets", json=_payload(priority="CRITICAL"), headers=auth(reporter))

    response = client.get(
        "/tickets",
        params={"priority": "LOW"},
        headers=auth(dispatcher),
    )

    assert response.status_code == 200
    assert [ticket["priority"] for ticket in response.json()] == ["LOW"]
