from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.models.ticket_history import TicketHistory
from app.models.user import User
from tests.conftest import auth


def _create_ticket(client: TestClient, reporter: User) -> dict:
    response = client.post(
        "/tickets",
        json={
            "title": "Street light out on 42B",
            "type": "ELEVATOR_OUT_OF_SERVICE",
            "priority": "HIGH",
            "location_text": "Avenue Habib Bourguiba",
        },
        headers=auth(reporter),
    )
    assert response.status_code == 201

    return response.json()


def _assign(
    client: TestClient,
    db: Session,
    ticket_id: str,
    contractor: User,
    dispatcher: User,
) -> Assignment:
    response = client.post(
        f"/tickets/{ticket_id}/assign",
        json={"contractor_id": str(contractor.id)},
        headers=auth(dispatcher),
    )
    assert response.status_code == 201

    return db.get(Assignment, UUID(response.json()["id"]))


def _patch_status(
    client: TestClient,
    ticket_id: str,
    status: str,
    actor: User,
    comment: str | None = None,
) -> object:
    payload: dict[str, object] = {"status": status}
    if comment is not None:
        payload["comment"] = comment

    return client.patch(
        f"/tickets/{ticket_id}/status",
        json=payload,
        headers=auth(actor),
    )


def _history(db: Session, ticket_id: str) -> list[TicketHistory]:
    return list(
        db.execute(
            select(TicketHistory)
            .where(TicketHistory.ticket_id == UUID(ticket_id))
            .order_by(TicketHistory.created_at)
        )
        .scalars()
        .all()
    )


def _notifications(db: Session) -> list[Notification]:
    return list(db.execute(select(Notification)).scalars().all())


def test_valid_transition_updates_ticket_and_history(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, db, ticket["id"], contractor, dispatcher)

    response = _patch_status(client, ticket["id"], "IN_PROGRESS", actor=contractor)

    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"

    latest = _history(db, ticket["id"])[-1]
    assert latest.action == "WORK_STARTED"
    assert latest.old_status == "ASSIGNED"
    assert latest.new_status == "IN_PROGRESS"
    assert latest.user_id == contractor.id


def test_invalid_transition_is_rejected_and_changes_nothing(
    client: TestClient,
    db: Session,
    reporter: User,
    admin: User,
) -> None:
    """An admin may attempt anything, so what fails here is the workflow itself."""
    ticket = _create_ticket(client, reporter)

    response = _patch_status(client, ticket["id"], "RESOLVED", actor=admin)

    assert response.status_code == 409
    assert "OPEN" in response.json()["detail"]

    assert db.get(Ticket, UUID(ticket["id"])).status == "OPEN"
    assert len(_history(db, ticket["id"])) == 1
    assert _notifications(db) == []


def test_transition_to_same_status_is_rejected(
    client: TestClient,
    reporter: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    response = _patch_status(client, ticket["id"], "OPEN", actor=dispatcher)

    assert response.status_code == 409
    assert "already OPEN" in response.json()["detail"]


def test_assigning_via_status_endpoint_is_refused(
    client: TestClient,
    reporter: User,
    dispatcher: User,
) -> None:
    """Even a dispatcher must go through the assign endpoint, so that an
    assignment row always exists."""
    ticket = _create_ticket(client, reporter)

    response = _patch_status(client, ticket["id"], "ASSIGNED", actor=dispatcher)

    assert response.status_code == 409
    assert "assign" in response.json()["detail"].lower()


def test_status_change_notifies_others_but_not_the_actor(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, db, ticket["id"], contractor, dispatcher)

    _patch_status(client, ticket["id"], "IN_PROGRESS", actor=contractor)

    recipients = {
        notification.user_id
        for notification in _notifications(db)
        if notification.type == "STATUS_CHANGE"
    }
    assert recipients == {reporter.id}


def test_resolving_notifies_dispatchers(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, db, ticket["id"], contractor, dispatcher)
    _patch_status(client, ticket["id"], "IN_PROGRESS", actor=contractor)

    _patch_status(client, ticket["id"], "RESOLVED", actor=contractor)

    resolved_notifications = [
        notification
        for notification in _notifications(db)
        if notification.title == "Ticket moved to RESOLVED"
    ]
    recipients = {notification.user_id for notification in resolved_notifications}
    assert recipients == {reporter.id, dispatcher.id}
    assert all(
        notification.type == "STATUS_CHANGE" for notification in resolved_notifications
    )


def test_resolving_stamps_the_assignment(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    assignment = _assign(client, db, ticket["id"], contractor, dispatcher)

    _patch_status(client, ticket["id"], "IN_PROGRESS", actor=contractor)
    _patch_status(client, ticket["id"], "RESOLVED", actor=contractor)

    db.refresh(assignment)
    assert assignment.started_at is not None
    assert assignment.completed_at is not None


def test_full_workflow_reaches_closed(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, db, ticket["id"], contractor, dispatcher)

    for status, actor in (
        ("IN_PROGRESS", contractor),
        ("RESOLVED", contractor),
        ("CLOSED", dispatcher),
    ):
        assert _patch_status(client, ticket["id"], status, actor=actor).status_code == 200

    assert db.get(Ticket, UUID(ticket["id"])).status == "CLOSED"


def test_history_endpoint_returns_the_timeline_in_order(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, db, ticket["id"], contractor, dispatcher)
    _patch_status(
        client,
        ticket["id"],
        "IN_PROGRESS",
        actor=contractor,
        comment="On site",
    )
    _patch_status(client, ticket["id"], "RESOLVED", actor=contractor)

    response = client.get(
        f"/tickets/{ticket['id']}/history",
        headers=auth(dispatcher),
    )

    assert response.status_code == 200
    entries = response.json()
    assert [entry["action"] for entry in entries] == [
        "TICKET_CREATED",
        "ASSIGNED",
        "WORK_STARTED",
        "RESOLVED",
    ]
    assert entries[2]["comment"] == "On site"


def test_history_of_unknown_ticket_returns_404(
    client: TestClient,
    dispatcher: User,
) -> None:
    response = client.get(f"/tickets/{uuid4()}/history", headers=auth(dispatcher))

    assert response.status_code == 404


def test_status_change_without_a_token_is_rejected(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    """There is no longer an actor field to forge: no token, no transition."""
    ticket = _create_ticket(client, reporter)
    _assign(client, db, ticket["id"], contractor, dispatcher)

    response = client.patch(
        f"/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS", "actor_id": str(contractor.id)},
    )

    assert response.status_code == 401
    assert db.get(Ticket, UUID(ticket["id"])).status == "ASSIGNED"
