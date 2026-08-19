from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models.assignment import Assignment
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.models.ticket_history import TicketHistory
from app.models.user import User
from tests.conftest import auth, make_user


def _create_ticket(
    client: TestClient,
    reporter: User,
    *,
    type: str = "OUTAGE",
    priority: str = "HIGH",
) -> dict:
    response = client.post(
        "/tickets",
        json={
            "title": "Street light out on 42B",
            "type": type,
            "priority": priority,
            "location_text": "Avenue Habib Bourguiba",
            "latitude": 36.80,
            "longitude": 10.18,
        },
        headers=auth(reporter),
    )
    assert response.status_code == 201

    return response.json()


def _assign(
    client: TestClient,
    ticket_id: str,
    contractor: User,
    dispatcher: User,
    notes: str | None = None,
) -> object:
    payload: dict[str, object] = {"contractor_id": str(contractor.id)}
    if notes is not None:
        payload["notes"] = notes

    return client.post(
        f"/tickets/{ticket_id}/assign",
        json=payload,
        headers=auth(dispatcher),
    )


def _assignments(db: Session, ticket_id: str) -> list[Assignment]:
    return list(
        db.execute(
            select(Assignment)
            .where(Assignment.ticket_id == UUID(ticket_id))
            .order_by(Assignment.assigned_at)
        )
        .scalars()
        .all()
    )


def test_assigning_moves_ticket_to_assigned_and_records_history(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    response = _assign(client, ticket["id"], contractor, dispatcher, notes="Night shift")

    assert response.status_code == 201
    body = response.json()
    assert body["contractor_id"] == str(contractor.id)
    assert body["assigned_by"] == str(dispatcher.id)
    assert body["notes"] == "Night shift"
    assert body["accepted_at"] is None

    assert db.get(Ticket, UUID(ticket["id"])).status == "ASSIGNED"

    entry = db.execute(
        select(TicketHistory)
        .where(TicketHistory.ticket_id == UUID(ticket["id"]))
        .order_by(TicketHistory.created_at.desc())
    ).scalars().first()
    assert entry.action == "ASSIGNED"
    assert entry.old_status == "OPEN"
    assert entry.new_status == "ASSIGNED"
    assert entry.meta["contractor_id"] == str(contractor.id)
    assert entry.user_id == dispatcher.id


def test_assignment_notifies_the_worker_and_reporter(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    _assign(client, ticket["id"], contractor, dispatcher)

    notifications = list(db.execute(select(Notification)).scalars().all())
    by_user = {notification.user_id: notification for notification in notifications}

    assert set(by_user) == {contractor.id, reporter.id}
    assert by_user[contractor.id].type == "ASSIGNMENT"
    assert "HIGH" in by_user[contractor.id].message
    assert dispatcher.id not in by_user


def test_ticket_response_shows_the_assigned_worker(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    detail = client.get(f"/tickets/{ticket['id']}", headers=auth(reporter)).json()
    queue = client.get("/tickets", headers=auth(dispatcher)).json()

    assert detail["assigned_worker"]["name"] == contractor.name
    assert queue[0]["assigned_worker"]["id"] == str(contractor.id)


def test_reassignment_appends_history_instead_of_overwriting(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    replacement = make_user(
        db,
        name="Bilal Backup",
        role=UserRole.CONTRACTOR,
        skills=["ELECTRICAL"],
    )
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    response = _assign(client, ticket["id"], replacement, dispatcher)

    assert response.status_code == 201
    rows = _assignments(db, ticket["id"])
    assert [row.contractor_id for row in rows] == [contractor.id, replacement.id]

    # The replaced worker is told, and the ticket stays ASSIGNED.
    assert db.get(Ticket, UUID(ticket["id"])).status == "ASSIGNED"
    reassignment_notice = db.execute(
        select(Notification).where(Notification.title == "Job reassigned")
    ).scalars().one()
    assert reassignment_notice.user_id == contractor.id

    latest = db.execute(
        select(TicketHistory)
        .where(TicketHistory.ticket_id == UUID(ticket["id"]))
        .order_by(TicketHistory.created_at.desc())
    ).scalars().first()
    assert latest.meta["reassigned_from"] == str(contractor.id)


def test_assigning_the_same_worker_twice_is_rejected(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    response = _assign(client, ticket["id"], contractor, dispatcher)

    assert response.status_code == 409
    assert "already assigned" in response.json()["detail"]


def test_cannot_assign_a_ticket_being_worked_on(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    replacement = make_user(db, name="Bilal Backup", role=UserRole.CONTRACTOR)
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)
    client.patch(
        f"/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth(contractor),
    )

    response = _assign(client, ticket["id"], replacement, dispatcher)

    assert response.status_code == 409
    assert "IN_PROGRESS" in response.json()["detail"]


def test_only_workers_can_be_assigned(
    client: TestClient,
    reporter: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    response = _assign(client, ticket["id"], reporter, dispatcher)

    assert response.status_code == 422
    assert "not a Contractor" in response.json()["detail"]


def test_assigning_an_unknown_worker_returns_404(
    client: TestClient,
    reporter: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    response = client.post(
        f"/tickets/{ticket['id']}/assign",
        json={"contractor_id": str(uuid4())},
        headers=auth(dispatcher),
    )

    assert response.status_code == 404


def test_accepting_stamps_the_assignment_and_notifies_the_dispatcher(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    response = client.post(
        f"/tickets/{ticket['id']}/accept",
        headers=auth(contractor),
    )

    assert response.status_code == 200
    assert response.json()["accepted_at"] is not None
    # Acceptance is not a status change.
    assert db.get(Ticket, UUID(ticket["id"])).status == "ASSIGNED"

    accepted_notice = db.execute(
        select(Notification).where(Notification.title == "Assignment accepted")
    ).scalars().one()
    assert accepted_notice.user_id == dispatcher.id

    latest = db.execute(
        select(TicketHistory)
        .where(TicketHistory.ticket_id == UUID(ticket["id"]))
        .order_by(TicketHistory.created_at.desc())
    ).scalars().first()
    assert latest.action == "ASSIGNMENT_ACCEPTED"


def test_only_the_assigned_worker_can_accept(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    intruder = make_user(db, name="Bilal Backup", role=UserRole.CONTRACTOR)
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    response = client.post(
        f"/tickets/{ticket['id']}/accept",
        headers=auth(intruder),
    )

    assert response.status_code == 403


def test_accepting_twice_is_rejected(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)
    client.post(f"/tickets/{ticket['id']}/accept", headers=auth(contractor))

    response = client.post(f"/tickets/{ticket['id']}/accept", headers=auth(contractor))

    assert response.status_code == 409


def test_accepting_an_unassigned_ticket_is_rejected(
    client: TestClient,
    reporter: User,
    contractor: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    response = client.post(f"/tickets/{ticket['id']}/accept", headers=auth(contractor))

    assert response.status_code == 409


def test_starting_work_implies_acceptance(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    client.patch(
        f"/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth(contractor),
    )

    assignment = _assignments(db, ticket["id"])[-1]
    db.refresh(assignment)
    assert assignment.accepted_at is not None
    assert assignment.started_at is not None


def test_worker_sees_only_their_own_jobs(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    other = make_user(db, name="Bilal Backup", role=UserRole.CONTRACTOR)
    mine = _create_ticket(client, reporter, priority="CRITICAL")
    theirs = _create_ticket(client, reporter)
    _assign(client, mine["id"], contractor, dispatcher)
    _assign(client, theirs["id"], other, dispatcher)

    response = client.get(
        f"/workers/{contractor.id}/tickets",
        headers=auth(dispatcher),
    )

    assert response.status_code == 200
    assert [ticket["id"] for ticket in response.json()] == [mine["id"]]

    # ...and the worker's own view agrees, without naming an id.
    own = client.get("/workers/me/tickets", headers=auth(contractor))
    assert [ticket["id"] for ticket in own.json()] == [mine["id"]]


def test_reassignment_moves_the_job_off_the_previous_worker(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    replacement = make_user(db, name="Bilal Backup", role=UserRole.CONTRACTOR)
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)
    _assign(client, ticket["id"], replacement, dispatcher)

    headers = auth(dispatcher)
    assert client.get(f"/workers/{contractor.id}/tickets", headers=headers).json() == []
    assert (
        len(client.get(f"/workers/{replacement.id}/tickets", headers=headers).json())
        == 1
    )


def test_worker_active_only_filter_hides_closed_jobs(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)
    for status, actor in (
        ("IN_PROGRESS", contractor),
        ("RESOLVED", contractor),
        ("CLOSED", dispatcher),
    ):
        client.patch(
            f"/tickets/{ticket['id']}/status",
            json={"status": status},
            headers=auth(actor),
        )

    headers = auth(dispatcher)
    assert client.get(f"/workers/{contractor.id}/tickets", headers=headers).json() != []
    assert (
        client.get(
            f"/workers/{contractor.id}/tickets",
            params={"active_only": True},
            headers=headers,
        ).json()
        == []
    )


def test_workers_list_reports_workload(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    make_user(db, name="Bilal Backup", role=UserRole.CONTRACTOR, is_available=False)
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    headers = auth(dispatcher)
    workers = client.get("/workers", headers=headers).json()

    by_name = {worker["name"]: worker for worker in workers}
    assert set(by_name) == {contractor.name, "Bilal Backup"}
    assert by_name[contractor.name]["active_ticket_count"] == 1
    assert by_name["Bilal Backup"]["active_ticket_count"] == 0

    available = client.get(
        "/workers",
        params={"available": True},
        headers=headers,
    ).json()
    assert [worker["name"] for worker in available] == [contractor.name]

    electricians = client.get(
        "/workers",
        params={"skill": "ELECTRICAL"},
        headers=headers,
    ).json()
    assert [worker["name"] for worker in electricians] == [contractor.name]


def test_worker_listing_survives_an_odd_stored_email(
    client: TestClient,
    db: Session,
    dispatcher: User,
) -> None:
    """Reading users must not re-validate addresses; one odd row would 500 the list."""
    db.add(
        User(
            name="Legacy Worker",
            email="legacy@example.test",
            role=UserRole.CONTRACTOR.value,
            skills=[],
        )
    )
    db.commit()

    response = client.get("/workers", headers=auth(dispatcher))

    assert response.status_code == 200
    assert "Legacy Worker" in [worker["name"] for worker in response.json()]


def test_recommendations_rank_the_skilled_nearby_worker_first(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    make_user(
        db,
        name="Zoubeir Wrongskill",
        role=UserRole.CONTRACTOR,
        skills=["MECHANICAL"],
        latitude=36.81,
        longitude=10.19,
    )
    ticket = _create_ticket(client, reporter, type="OUTAGE")

    response = client.get(
        f"/tickets/{ticket['id']}/recommendations",
        headers=auth(dispatcher),
    )

    assert response.status_code == 200
    ranked = response.json()
    assert ranked[0]["worker_id"] == str(contractor.id)
    assert ranked[0]["score"] > ranked[1]["score"]
    assert any("ELECTRICAL" in reason for reason in ranked[0]["reasons"])


def test_recommendations_for_unknown_ticket_return_404(
    client: TestClient,
    dispatcher: User,
) -> None:
    response = client.get(
        f"/tickets/{uuid4()}/recommendations",
        headers=auth(dispatcher),
    )

    assert response.status_code == 404
