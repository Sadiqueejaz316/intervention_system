from dataclasses import dataclass
from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.base import WorkerCandidate
from app.domain.current import get_domain_adapter


def test_health_reports_domain_and_database(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "connected"


def test_domain_config_exposes_terminology(client: TestClient) -> None:
    response = client.get("/domain/config")

    assert response.status_code == 200
    body = response.json()
    assert body["domain_name"] == "Generic Intervention"
    assert body["worker_label"] == "Contractor"
    assert body["issue_types"] == ["GENERAL", "EQUIPMENT", "DAMAGE", "OUTAGE"]
    assert body["status_transitions"]["OPEN"] == ["ASSIGNED"]


def test_issue_types_endpoint(client: TestClient) -> None:
    response = client.get("/domain/issue-types")

    assert response.status_code == 200
    assert response.json() == get_domain_adapter().issue_types


def test_transitions_follow_the_workflow() -> None:
    adapter = get_domain_adapter()

    assert adapter.can_transition("OPEN", "ASSIGNED")
    assert adapter.can_transition("IN_PROGRESS", "RESOLVED")
    assert not adapter.can_transition("OPEN", "RESOLVED")
    assert not adapter.can_transition("CLOSED", "OPEN")


@dataclass
class FakeTicket:
    type: str = "OUTAGE"
    priority: str = "HIGH"
    latitude: float | None = 36.80
    longitude: float | None = 10.18


def test_rank_workers_prefers_skilled_available_and_close() -> None:
    adapter = get_domain_adapter()

    skilled = WorkerCandidate(
        id=uuid4(),
        name="Skilled and nearby",
        skills=["ELECTRICAL"],
        is_available=True,
        latitude=36.81,
        longitude=10.19,
        active_ticket_count=0,
    )
    unskilled = WorkerCandidate(
        id=uuid4(),
        name="Wrong skill",
        skills=["MECHANICAL"],
        is_available=True,
        latitude=36.81,
        longitude=10.19,
        active_ticket_count=0,
    )
    busy = WorkerCandidate(
        id=uuid4(),
        name="Skilled but unavailable and loaded",
        skills=["ELECTRICAL"],
        is_available=False,
        latitude=36.81,
        longitude=10.19,
        active_ticket_count=5,
    )

    ranked = adapter.rank_workers(FakeTicket(), [unskilled, busy, skilled])

    assert [result.worker_id for result in ranked][0] == skilled.id
    assert ranked[0].score > ranked[1].score > ranked[2].score
    assert "Required skill matched: ELECTRICAL" in ranked[0].reasons
