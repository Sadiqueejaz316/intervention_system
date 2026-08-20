"""Live HTTP path for the trapped-person demo."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.domain.elevator import PERSON_TRAPPED
from app.models.user import User
from tests.conftest import auth, make_user


def test_full_emergency_workflow(
    client: TestClient,
    reporter: User,
    dispatcher: User,
    db: Session,
) -> None:
    sami = make_user(
        db,
        name="Sami Sparks",
        role=UserRole.CONTRACTOR,
        skills=["ELEVATOR_GENERAL", "ELEVATOR_EMERGENCY", "ELECTRICAL"],
        latitude=36.809,
        longitude=10.184,
    )
    make_user(
        db,
        name="Farid Faraway",
        role=UserRole.CONTRACTOR,
        skills=["ELEVATOR_GENERAL"],
        latitude=36.50,
        longitude=10.80,
        is_available=False,
    )

    created = client.post(
        "/tickets",
        json={
            "title": "People trapped in elevator",
            "description": "Two residents are trapped inside",
            "type": PERSON_TRAPPED,
            "metadata": {
                "building_name": "Building A",
                "elevator_id": "ELV-02",
                "floor": 7,
                "people_trapped": 2,
                "communication_possible": True,
            },
        },
        headers=auth(reporter),
    )
    assert created.status_code == 201
    ticket = created.json()
    ticket_id = ticket["id"]
    assert ticket["status"] == "OPEN"
    assert ticket["priority"] == "CRITICAL"
    assert ticket["is_emergency"] is True

    queue = client.get("/tickets", headers=auth(dispatcher)).json()
    assert queue[0]["id"] == ticket_id

    ranked = client.get(
        f"/tickets/{ticket_id}/recommendations",
        headers=auth(dispatcher),
    ).json()
    assert ranked[0]["worker_id"] == str(sami.id)
    assert any(
        "emergency certification" in reason.lower() for reason in ranked[0]["reasons"]
    )

    assigned = client.post(
        f"/tickets/{ticket_id}/assign",
        json={"contractor_id": str(sami.id)},
        headers=auth(dispatcher),
    )
    assert assigned.status_code == 201

    accepted = client.post(
        f"/tickets/{ticket_id}/accept",
        headers=auth(sami),
    )
    assert accepted.status_code == 200
    assert accepted.json()["accepted_at"] is not None

    started = client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth(sami),
    )
    assert started.status_code == 200
    assert started.json()["status"] == "IN_PROGRESS"

    resolved = client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "RESOLVED", "comment": "Residents out; elevator isolated."},
        headers=auth(sami),
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"

    closed = client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "CLOSED"},
        headers=auth(dispatcher),
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"

    history = client.get(
        f"/tickets/{ticket_id}/history",
        headers=auth(dispatcher),
    ).json()
    actions = [entry["action"] for entry in history]
    assert actions[0] == "TICKET_CREATED"
    assert "Emergency ticket created" in history[0]["comment"]
    assert "ASSIGNED" in actions
    assert "ASSIGNMENT_ACCEPTED" in actions
    assert "WORK_STARTED" in actions
    assert "RESOLVED" in actions
    assert "CLOSED" in actions
    assert all("created_at" in entry for entry in history)

    technician_mail = client.get("/notifications", headers=auth(sami)).json()
    assert any("EMERGENCY" in item["title"] for item in technician_mail)

    reporter_mail = client.get("/notifications", headers=auth(reporter)).json()
    assert any(item["ticket_id"] == ticket_id for item in reporter_mail)

    forbidden = client.get(f"/tickets/{ticket_id}", headers=auth(reporter))
    assert forbidden.status_code == 200
    stranger = make_user(db, name="Other Resident", role=UserRole.REPORTER)
    blocked = client.get(f"/tickets/{ticket_id}", headers=auth(stranger))
    assert blocked.status_code == 403
