from dataclasses import dataclass
from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.base import WorkerCandidate
from app.domain.current import get_domain_adapter
from app.domain.elevator import PERSON_TRAPPED
from app.models.user import User
from tests.conftest import auth


@dataclass
class FakeTicket:
    type: str = "LIGHTING_FAILURE"
    priority: str = "HIGH"
    latitude: float | None = 36.80
    longitude: float | None = 10.18


def _trapped_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "People trapped in elevator",
        "description": "Two residents are trapped inside",
        "type": PERSON_TRAPPED,
        "priority": "LOW",
        "metadata": {
            "building_name": "Building A",
            "elevator_id": "ELV-02",
            "floor": 7,
            "people_trapped": 2,
            "communication_possible": True,
        },
    }
    payload.update(overrides)
    return payload


def test_person_trapped_is_an_issue_type() -> None:
    adapter = get_domain_adapter()
    assert PERSON_TRAPPED in adapter.issue_types
    assert adapter.is_emergency_type(PERSON_TRAPPED)
    assert not adapter.is_emergency_type("DOOR_MALFUNCTION")


def test_person_trapped_becomes_critical_emergency(
    client: TestClient,
    reporter: User,
) -> None:
    response = client.post("/tickets", json=_trapped_payload(), headers=auth(reporter))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "OPEN"
    assert body["priority"] == "CRITICAL"
    assert body["is_emergency"] is True
    assert body["metadata"]["is_emergency"] is True
    assert body["metadata"]["people_trapped"] == 2
    assert body["type"] == PERSON_TRAPPED


def test_person_trapped_cannot_be_downgraded(
    client: TestClient,
    reporter: User,
) -> None:
    response = client.post(
        "/tickets",
        json=_trapped_payload(priority="MEDIUM"),
        headers=auth(reporter),
    )

    assert response.status_code == 201
    assert response.json()["priority"] == "CRITICAL"


def test_person_trapped_requires_people_count(
    client: TestClient,
    reporter: User,
) -> None:
    response = client.post(
        "/tickets",
        json=_trapped_payload(
            metadata={"building_name": "Building A", "people_trapped": 0}
        ),
        headers=auth(reporter),
    )

    assert response.status_code == 422
    assert "people_trapped" in response.json()["detail"]


def test_normal_issues_are_not_emergencies(
    client: TestClient,
    reporter: User,
) -> None:
    response = client.post(
        "/tickets",
        json={
            "title": "Cabin lights out",
            "type": "LIGHTING_FAILURE",
            "priority": "LOW",
        },
        headers=auth(reporter),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["priority"] == "LOW"
    assert body["is_emergency"] is False


def test_emergency_ranks_certified_available_nearby_idle_first() -> None:
    adapter = get_domain_adapter()
    ticket = FakeTicket(type=PERSON_TRAPPED, priority="CRITICAL")

    certified = WorkerCandidate(
        id=uuid4(),
        name="Certified nearby",
        skills=["ELEVATOR_EMERGENCY", "ELEVATOR_GENERAL"],
        is_available=True,
        latitude=36.81,
        longitude=10.19,
        active_ticket_count=0,
    )
    uncertified = WorkerCandidate(
        id=uuid4(),
        name="General only",
        skills=["ELEVATOR_GENERAL"],
        is_available=True,
        latitude=36.81,
        longitude=10.19,
        active_ticket_count=0,
    )
    busy = WorkerCandidate(
        id=uuid4(),
        name="Certified but busy",
        skills=["ELEVATOR_EMERGENCY"],
        is_available=False,
        latitude=36.81,
        longitude=10.19,
        active_ticket_count=5,
    )
    far = WorkerCandidate(
        id=uuid4(),
        name="Certified far away",
        skills=["ELEVATOR_EMERGENCY"],
        is_available=True,
        latitude=36.40,
        longitude=10.70,
        active_ticket_count=0,
    )
    loaded = WorkerCandidate(
        id=uuid4(),
        name="Certified with jobs",
        skills=["ELEVATOR_EMERGENCY"],
        is_available=True,
        latitude=36.81,
        longitude=10.19,
        active_ticket_count=3,
    )

    ranked = adapter.rank_workers(ticket, [uncertified, busy, far, loaded, certified])
    by_name = {result.name: result for result in ranked}

    assert ranked[0].worker_id == certified.id
    assert "Elevator emergency certification matched" in ranked[0].reasons
    assert "Available for emergency dispatch" in ranked[0].reasons
    assert "No active emergency jobs" in ranked[0].reasons
    assert any("km from building" in reason for reason in ranked[0].reasons)
    assert "Missing required skill: ELEVATOR_EMERGENCY" in by_name["General only"].reasons
    assert by_name["Certified nearby"].score > by_name["Certified far away"].score
    assert by_name["Certified nearby"].score > by_name["Certified with jobs"].score
    assert by_name["Certified nearby"].score > by_name["Certified but busy"].score


def test_normal_ranking_prefers_skill_match() -> None:
    adapter = get_domain_adapter()
    skilled = WorkerCandidate(
        id=uuid4(),
        name="Electrician",
        skills=["ELECTRICAL"],
        is_available=True,
        latitude=36.81,
        longitude=10.19,
        active_ticket_count=0,
    )
    other = WorkerCandidate(
        id=uuid4(),
        name="Door specialist",
        skills=["DOOR_SYSTEM"],
        is_available=True,
        latitude=36.81,
        longitude=10.19,
        active_ticket_count=0,
    )

    ranked = adapter.rank_workers(FakeTicket(), [other, skilled])
    assert ranked[0].worker_id == skilled.id
    assert "Required skill matched: ELECTRICAL" in ranked[0].reasons


def test_emergency_appears_before_ordinary_critical(
    client: TestClient,
    reporter: User,
    dispatcher: User,
) -> None:
    client.post(
        "/tickets",
        json={
            "title": "Urgent but empty cabin",
            "type": "ELEVATOR_OUT_OF_SERVICE",
            "priority": "CRITICAL",
        },
        headers=auth(reporter),
    )
    client.post("/tickets", json=_trapped_payload(), headers=auth(reporter))

    response = client.get("/tickets", headers=auth(dispatcher))
    titles = [ticket["title"] for ticket in response.json()]

    assert titles[0] == "People trapped in elevator"
    assert titles[1] == "Urgent but empty cabin"


def test_older_ticket_wins_within_the_same_priority(
    client: TestClient,
    reporter: User,
    dispatcher: User,
) -> None:
    client.post(
        "/tickets",
        json={"title": "First high", "type": "DOOR_MALFUNCTION", "priority": "HIGH"},
        headers=auth(reporter),
    )
    client.post(
        "/tickets",
        json={"title": "Second high", "type": "DOOR_MALFUNCTION", "priority": "HIGH"},
        headers=auth(reporter),
    )

    titles = [
        ticket["title"]
        for ticket in client.get("/tickets", headers=auth(dispatcher)).json()
    ]
    assert titles.index("First high") < titles.index("Second high")


def test_emergency_notifies_dispatchers(
    client: TestClient,
    reporter: User,
    dispatcher: User,
) -> None:
    created = client.post(
        "/tickets", json=_trapped_payload(), headers=auth(reporter)
    ).json()

    inbox = client.get("/notifications", headers=auth(dispatcher)).json()
    assert inbox
    assert inbox[0]["ticket_id"] == created["id"]
    assert inbox[0]["type"] == "ESCALATION"
    assert "EMERGENCY" in inbox[0]["title"]
    assert "ELV-02" in inbox[0]["message"]
    assert "Building A" in inbox[0]["message"]


def test_operations_stats_count_emergencies(
    client: TestClient,
    reporter: User,
    dispatcher: User,
) -> None:
    client.post("/tickets", json=_trapped_payload(), headers=auth(reporter))
    client.post(
        "/tickets",
        json={"title": "Noise", "type": "ABNORMAL_NOISE", "priority": "MEDIUM"},
        headers=auth(reporter),
    )

    stats = client.get("/tickets/stats", headers=auth(dispatcher)).json()
    assert stats["total"] == 2
    assert stats["emergency"] == 1
    assert stats["open"] == 2
