"""Role, ownership and visibility rules.

The backend is the only thing standing between a user and somebody else's data:
none of these rules may depend on the frontend hiding a button.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models.notification import Notification
from app.models.ticket_history import TicketHistory
from app.models.user import User
from tests.conftest import auth, make_user


@pytest.fixture
def other_reporter(db: Session) -> User:
    return make_user(db, name="Omar Otherreporter", role=UserRole.REPORTER)


@pytest.fixture
def other_contractor(db: Session) -> User:
    return make_user(
        db,
        name="Bilal Backup",
        role=UserRole.CONTRACTOR,
        skills=["ELECTRICAL"],
    )


def _create_ticket(
    client: TestClient,
    reporter: User,
    title: str = "Street light out on 42B",
) -> dict:
    response = client.post(
        "/tickets",
        json={
            "title": title,
            "type": "ELEVATOR_OUT_OF_SERVICE",
            "priority": "HIGH",
            "location_text": "Avenue Habib Bourguiba",
        },
        headers=auth(reporter),
    )
    assert response.status_code == 201

    return response.json()


def _assign(client: TestClient, ticket_id: str, contractor: User, actor: User) -> object:
    return client.post(
        f"/tickets/{ticket_id}/assign",
        json={"contractor_id": str(contractor.id)},
        headers=auth(actor),
    )


def _status(client: TestClient, ticket_id: str, status: str, actor: User) -> object:
    return client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": status},
        headers=auth(actor),
    )


def _take_to_resolved(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> dict:
    ticket = _create_ticket(client, reporter)
    assert _assign(client, ticket["id"], contractor, dispatcher).status_code == 201
    assert _status(client, ticket["id"], "IN_PROGRESS", contractor).status_code == 200
    assert _status(client, ticket["id"], "RESOLVED", contractor).status_code == 200

    return ticket


# --------------------------------------------------------------------------- #
# Assignment                                                                    #
# --------------------------------------------------------------------------- #


def test_reporter_cannot_assign(
    client: TestClient,
    reporter: User,
    contractor: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    assert _assign(client, ticket["id"], contractor, reporter).status_code == 403


def test_contractor_cannot_assign(
    client: TestClient,
    reporter: User,
    contractor: User,
    other_contractor: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    assert _assign(client, ticket["id"], other_contractor, contractor).status_code == 403


def test_dispatcher_can_assign(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    assert _assign(client, ticket["id"], contractor, dispatcher).status_code == 201


def test_admin_can_assign(
    client: TestClient,
    reporter: User,
    contractor: User,
    admin: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    assert _assign(client, ticket["id"], contractor, admin).status_code == 201


# --------------------------------------------------------------------------- #
# Workflow ownership                                                            #
# --------------------------------------------------------------------------- #


def test_contractor_cannot_start_another_contractors_job(
    client: TestClient,
    reporter: User,
    contractor: User,
    other_contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    response = _status(client, ticket["id"], "IN_PROGRESS", other_contractor)

    assert response.status_code == 403
    assert "assigned" in response.json()["detail"]


def test_contractor_cannot_resolve_another_contractors_job(
    client: TestClient,
    reporter: User,
    contractor: User,
    other_contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)
    _status(client, ticket["id"], "IN_PROGRESS", contractor)

    assert _status(client, ticket["id"], "RESOLVED", other_contractor).status_code == 403


def test_contractor_cannot_accept_another_contractors_job(
    client: TestClient,
    reporter: User,
    contractor: User,
    other_contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    response = client.post(
        f"/tickets/{ticket['id']}/accept",
        headers=auth(other_contractor),
    )

    assert response.status_code == 403


def test_reporter_cannot_start_work_on_their_own_ticket(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    assert _status(client, ticket["id"], "IN_PROGRESS", reporter).status_code == 403


def test_reporter_cannot_touch_another_reporters_ticket(
    client: TestClient,
    reporter: User,
    other_reporter: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    assert client.get(
        f"/tickets/{ticket['id']}",
        headers=auth(other_reporter),
    ).status_code == 403
    assert _status(client, ticket["id"], "CLOSED", other_reporter).status_code == 403


# --------------------------------------------------------------------------- #
# Closing                                                                       #
# --------------------------------------------------------------------------- #


def test_contractor_cannot_close_a_resolved_ticket(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _take_to_resolved(client, reporter, contractor, dispatcher)

    assert _status(client, ticket["id"], "CLOSED", contractor).status_code == 403


def test_reporter_cannot_close_a_resolved_ticket(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _take_to_resolved(client, reporter, contractor, dispatcher)

    assert _status(client, ticket["id"], "CLOSED", reporter).status_code == 403


def test_dispatcher_can_close_a_resolved_ticket(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _take_to_resolved(client, reporter, contractor, dispatcher)

    response = _status(client, ticket["id"], "CLOSED", dispatcher)

    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"


def test_admin_can_close_a_resolved_ticket(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
    admin: User,
) -> None:
    ticket = _take_to_resolved(client, reporter, contractor, dispatcher)

    assert _status(client, ticket["id"], "CLOSED", admin).status_code == 200


# --------------------------------------------------------------------------- #
# Ticket visibility                                                             #
# --------------------------------------------------------------------------- #


def test_reporter_only_lists_their_own_tickets(
    client: TestClient,
    reporter: User,
    other_reporter: User,
) -> None:
    mine = _create_ticket(client, reporter, title="My report")
    _create_ticket(client, other_reporter, title="Their report")

    response = client.get("/tickets", headers=auth(reporter))

    assert response.status_code == 200
    assert [ticket["id"] for ticket in response.json()] == [mine["id"]]


def test_reporter_cannot_widen_the_queue_with_a_query_parameter(
    client: TestClient,
    reporter: User,
    other_reporter: User,
) -> None:
    _create_ticket(client, other_reporter, title="Their report")

    response = client.get(
        "/tickets",
        params={"reporter_id": str(other_reporter.id)},
        headers=auth(reporter),
    )

    assert response.json() == []


def test_contractor_only_lists_tickets_assigned_to_them(
    client: TestClient,
    reporter: User,
    contractor: User,
    other_contractor: User,
    dispatcher: User,
) -> None:
    mine = _create_ticket(client, reporter, title="My job")
    theirs = _create_ticket(client, reporter, title="Their job")
    _assign(client, mine["id"], contractor, dispatcher)
    _assign(client, theirs["id"], other_contractor, dispatcher)

    response = client.get("/tickets", headers=auth(contractor))

    assert [ticket["id"] for ticket in response.json()] == [mine["id"]]


def test_dispatcher_lists_every_ticket(
    client: TestClient,
    reporter: User,
    other_reporter: User,
    dispatcher: User,
) -> None:
    _create_ticket(client, reporter, title="One")
    _create_ticket(client, other_reporter, title="Two")

    response = client.get("/tickets", headers=auth(dispatcher))

    assert {ticket["title"] for ticket in response.json()} == {"One", "Two"}


def test_contractor_can_view_the_ticket_they_are_working_on(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)

    assert client.get(
        f"/tickets/{ticket['id']}",
        headers=auth(contractor),
    ).status_code == 403

    _assign(client, ticket["id"], contractor, dispatcher)

    assert client.get(
        f"/tickets/{ticket['id']}",
        headers=auth(contractor),
    ).status_code == 200


# --------------------------------------------------------------------------- #
# Workers and recommendations                                                   #
# --------------------------------------------------------------------------- #


def test_only_staff_may_enumerate_workers(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
    admin: User,
) -> None:
    assert client.get("/workers", headers=auth(reporter)).status_code == 403
    assert client.get("/workers", headers=auth(contractor)).status_code == 403
    assert client.get("/workers", headers=auth(dispatcher)).status_code == 200
    assert client.get("/workers", headers=auth(admin)).status_code == 200


def test_contractor_sees_their_own_worker_profile(
    client: TestClient,
    contractor: User,
) -> None:
    response = client.get("/workers/me", headers=auth(contractor))

    assert response.status_code == 200
    assert response.json()["id"] == str(contractor.id)


def test_contractor_cannot_read_another_workers_jobs(
    client: TestClient,
    contractor: User,
    other_contractor: User,
) -> None:
    response = client.get(
        f"/workers/{other_contractor.id}/tickets",
        headers=auth(contractor),
    )

    assert response.status_code == 403


def test_only_staff_may_read_recommendations(
    client: TestClient,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    path = f"/tickets/{ticket['id']}/recommendations"

    assert client.get(path, headers=auth(reporter)).status_code == 403
    assert client.get(path, headers=auth(contractor)).status_code == 403
    assert client.get(path, headers=auth(dispatcher)).status_code == 200


def test_a_skill_mismatch_warns_but_never_blocks_assignment(
    client: TestClient,
    db: Session,
    reporter: User,
    dispatcher: User,
) -> None:
    """Dispatcher override survives authorization: scoring stays advisory."""
    mismatched = make_user(
        db,
        name="Zoubeir Wrongskill",
        role=UserRole.CONTRACTOR,
        skills=["MECHANICAL"],
    )
    ticket = _create_ticket(client, reporter)

    ranked = client.get(
        f"/tickets/{ticket['id']}/recommendations",
        headers=auth(dispatcher),
    ).json()
    warning = next(
        result for result in ranked if result["worker_id"] == str(mismatched.id)
    )
    assert any("skill" in reason.lower() for reason in warning["reasons"])

    assert _assign(client, ticket["id"], mismatched, dispatcher).status_code == 201


# --------------------------------------------------------------------------- #
# Notifications                                                                 #
# --------------------------------------------------------------------------- #


def test_notifications_only_ever_show_your_own(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    for user in (reporter, contractor):
        inbox = client.get("/notifications", headers=auth(user)).json()

        assert inbox != []
        assert {entry["user_id"] for entry in inbox} == {str(user.id)}

    stored = db.execute(select(Notification)).scalars().all()
    assert len(stored) > len(client.get("/notifications", headers=auth(reporter)).json())


def test_marking_someone_elses_notification_read_is_forbidden(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    theirs = db.execute(
        select(Notification).where(Notification.user_id == contractor.id)
    ).scalars().first()

    response = client.patch(
        f"/notifications/{theirs.id}/read",
        headers=auth(reporter),
    )

    assert response.status_code == 403
    db.refresh(theirs)
    assert theirs.is_read is False


def test_marking_your_own_notification_read_works(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    dispatcher: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    mine = db.execute(
        select(Notification).where(Notification.user_id == reporter.id)
    ).scalars().first()

    response = client.patch(f"/notifications/{mine.id}/read", headers=auth(reporter))

    assert response.status_code == 200
    assert response.json()["is_read"] is True
    assert client.get(
        "/notifications",
        params={"unread_only": True},
        headers=auth(reporter),
    ).json() == []


def test_notifications_require_a_token(client: TestClient) -> None:
    assert client.get("/notifications").status_code == 401


# --------------------------------------------------------------------------- #
# History                                                                       #
# --------------------------------------------------------------------------- #


def test_history_follows_the_same_visibility_rules(
    client: TestClient,
    reporter: User,
    other_reporter: User,
    contractor: User,
    other_contractor: User,
    dispatcher: User,
    admin: User,
) -> None:
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)
    path = f"/tickets/{ticket['id']}/history"

    assert client.get(path, headers=auth(reporter)).status_code == 200
    assert client.get(path, headers=auth(contractor)).status_code == 200
    assert client.get(path, headers=auth(dispatcher)).status_code == 200
    assert client.get(path, headers=auth(admin)).status_code == 200

    assert client.get(path, headers=auth(other_reporter)).status_code == 403
    assert client.get(path, headers=auth(other_contractor)).status_code == 403


def test_history_records_the_authenticated_user_not_a_client_supplied_id(
    client: TestClient,
    db: Session,
    reporter: User,
    contractor: User,
    other_contractor: User,
    dispatcher: User,
) -> None:
    """A leftover actor_id in the payload must have no effect whatsoever."""
    ticket = _create_ticket(client, reporter)
    _assign(client, ticket["id"], contractor, dispatcher)

    response = client.patch(
        f"/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS", "actor_id": str(other_contractor.id)},
        headers=auth(contractor),
    )
    assert response.status_code == 200

    latest = db.execute(
        select(TicketHistory)
        .where(TicketHistory.ticket_id == ticket["id"])
        .order_by(TicketHistory.created_at.desc())
    ).scalars().first()

    assert latest.user_id == contractor.id
