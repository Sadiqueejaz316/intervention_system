from fastapi.testclient import TestClient

from app.domain.current import get_domain_adapter
from app.domain.elevator import PERSON_TRAPPED, ElevatorDomainAdapter


def test_health_reports_domain_and_database(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "connected"
    assert "Elevator" in response.json()["domain"]


def test_domain_config_exposes_elevator_terminology(client: TestClient) -> None:
    response = client.get("/domain/config")

    assert response.status_code == 200
    body = response.json()
    assert body["domain_name"] == "Elevator Service — Housing Co-ops"
    assert body["worker_label"] == "Elevator Technician"
    values = [item["value"] for item in body["issue_types"]]
    assert PERSON_TRAPPED in values
    trapped = next(
        item for item in body["issue_types"] if item["value"] == PERSON_TRAPPED
    )
    assert trapped["emergency"] is True
    assert trapped["label"]
    assert body["status_transitions"]["OPEN"] == ["ASSIGNED"]
    assert "ELEVATOR_EMERGENCY" in body["skill_vocabulary"]
    assert body["metadata_hint"]["emergency_type"] == PERSON_TRAPPED


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


def test_active_adapter_is_elevator() -> None:
    assert isinstance(get_domain_adapter(), ElevatorDomainAdapter)
