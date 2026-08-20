"""Elevator service for housing cooperatives.

The operational special case is PERSON_TRAPPED: that issue is always a CRITICAL
emergency. Everything else is ordinary elevator maintenance.
"""

from typing import Any

from app.core.enums import TicketPriority, TicketStatus
from app.domain.base import (
    DomainAdapter,
    TicketLike,
    WorkerCandidate,
    WorkerScore,
    haversine_km,
)

PERSON_TRAPPED = "PERSON_TRAPPED"

ISSUE_TYPES = [
    PERSON_TRAPPED,
    "ELEVATOR_OUT_OF_SERVICE",
    "DOOR_MALFUNCTION",
    "ELEVATOR_STOPPING",
    "ABNORMAL_NOISE",
    "CONTROL_PANEL_FAILURE",
    "LIGHTING_FAILURE",
    "OTHER",
]

BUILDINGS: list[dict[str, Any]] = [
    {
        "name": "Building A",
        "address": "12 Rue de la Liberte, Tunis",
        "latitude": 36.8065,
        "longitude": 10.1815,
    },
    {
        "name": "Building B",
        "address": "8 Avenue Habib Bourguiba, Tunis",
        "latitude": 36.8008,
        "longitude": 10.1807,
    },
    {
        "name": "Building C",
        "address": "22 Avenue Mohammed V, Tunis",
        "latitude": 36.8120,
        "longitude": 10.1850,
    },
    {
        "name": "Building D",
        "address": "4 Cite Olympique, Tunis",
        "latitude": 36.8400,
        "longitude": 10.1950,
    },
]

ELEVATOR_IDS = ["ELV-01", "ELV-02", "ELV-03", "ELV-04"]


class ElevatorDomainAdapter(DomainAdapter):
    domain_name = "Elevator Service — Housing Co-ops"
    worker_label = "Elevator Technician"
    issue_types = ISSUE_TYPES
    emergency_types = frozenset({PERSON_TRAPPED})

    issue_type_labels = {
        PERSON_TRAPPED: "Person trapped in elevator",
        "ELEVATOR_OUT_OF_SERVICE": "Elevator not working",
        "DOOR_MALFUNCTION": "Doors malfunctioning",
        "ELEVATOR_STOPPING": "Elevator stopping unexpectedly",
        "ABNORMAL_NOISE": "Unusual noise",
        "CONTROL_PANEL_FAILURE": "Control panel problem",
        "LIGHTING_FAILURE": "Lighting problem",
        "OTHER": "Other",
    }

    issue_type_descriptions = {
        PERSON_TRAPPED: "Elevator cabin has people trapped inside",
        "ELEVATOR_OUT_OF_SERVICE": "The elevator will not move or is out of service",
        "DOOR_MALFUNCTION": "Doors stuck, reversing, or not closing",
        "ELEVATOR_STOPPING": "Cabin stopping between floors or repeatedly",
        "ABNORMAL_NOISE": "Grinding, banging, or other unusual noise",
        "CONTROL_PANEL_FAILURE": "Buttons, display, or alarm not responding",
        "LIGHTING_FAILURE": "Cabin or landing lights out",
        "OTHER": "Anything else affecting an elevator in the co-op",
    }

    skill_vocabulary = [
        "ELEVATOR_GENERAL",
        "ELEVATOR_EMERGENCY",
        "DOOR_SYSTEM",
        "ELECTRICAL",
        "CONTROL_SYSTEM",
        "HYDRAULIC",
        "TRACTION",
        "SAFETY_SYSTEM",
    ]

    skill_labels = {
        "ELEVATOR_GENERAL": "Elevator general",
        "ELEVATOR_EMERGENCY": "Elevator emergency",
        "DOOR_SYSTEM": "Door system",
        "ELECTRICAL": "Electrical",
        "CONTROL_SYSTEM": "Control system",
        "HYDRAULIC": "Hydraulic",
        "TRACTION": "Traction",
        "SAFETY_SYSTEM": "Safety system",
    }

    status_transitions = {
        TicketStatus.OPEN: [TicketStatus.ASSIGNED],
        TicketStatus.ASSIGNED: [TicketStatus.IN_PROGRESS],
        TicketStatus.IN_PROGRESS: [TicketStatus.RESOLVED],
        TicketStatus.RESOLVED: [TicketStatus.CLOSED],
        TicketStatus.CLOSED: [],
    }

    # Fast intake: only people_trapped is enforced for entrapment. Building and
    # elevator help the dispatcher but must not block a 112-adjacent report.
    required_metadata: dict[str, list[str]] = {}

    _skills_by_type = {
        PERSON_TRAPPED: ["ELEVATOR_EMERGENCY"],
        "ELEVATOR_OUT_OF_SERVICE": ["ELEVATOR_GENERAL"],
        "DOOR_MALFUNCTION": ["DOOR_SYSTEM"],
        "ELEVATOR_STOPPING": ["ELEVATOR_GENERAL"],
        "ABNORMAL_NOISE": ["ELEVATOR_GENERAL"],
        "CONTROL_PANEL_FAILURE": ["CONTROL_SYSTEM"],
        "LIGHTING_FAILURE": ["ELECTRICAL"],
        "OTHER": ["ELEVATOR_GENERAL"],
    }

    # Entrapment ranking: get a certified, free technician moving first.
    _emergency_skill_weight = 40
    _emergency_availability_weight = 35
    _emergency_distance_weight = 15
    _emergency_workload_weight = 10

    def get_required_skills(self, issue_type: str) -> list[str]:
        return list(self._skills_by_type.get(issue_type, []))

    def prepare_ticket(self, ticket_data: dict[str, Any]) -> dict[str, Any]:
        """Force PERSON_TRAPPED onto CRITICAL + emergency; fill location from metadata."""
        data = dict(ticket_data)
        metadata = dict(data.get("metadata") or {})
        issue_type = data.get("type")

        if self.is_emergency_type(str(issue_type) if issue_type else None):
            data["priority"] = TicketPriority.CRITICAL.value
            metadata["is_emergency"] = True
        else:
            metadata.setdefault("is_emergency", False)

        if not data.get("location_text"):
            where = " — ".join(
                part
                for part in (
                    _as_text(metadata.get("building_name")),
                    _as_text(metadata.get("elevator_id")),
                )
                if part
            )
            if where:
                data["location_text"] = where

        building = next(
            (
                item
                for item in BUILDINGS
                if item["name"] == metadata.get("building_name")
            ),
            None,
        )
        if building is not None:
            if data.get("latitude") is None:
                data["latitude"] = building["latitude"]
            if data.get("longitude") is None:
                data["longitude"] = building["longitude"]

        data["metadata"] = metadata
        return data

    def validate_ticket(self, ticket_data: dict[str, Any]) -> list[str]:
        errors = super().validate_ticket(ticket_data)
        issue_type = ticket_data.get("type")
        metadata = ticket_data.get("metadata") or {}
        priority = ticket_data.get("priority")

        if issue_type == PERSON_TRAPPED:
            if priority not in {TicketPriority.CRITICAL, TicketPriority.CRITICAL.value}:
                errors.append("A trapped-person ticket must be CRITICAL priority.")
            if metadata.get("is_emergency") is not True:
                errors.append("A trapped-person ticket must be marked as an emergency.")
            people = metadata.get("people_trapped")
            if not _is_positive_int(people):
                errors.append(
                    "people_trapped must be at least 1 for PERSON_TRAPPED."
                )

        return errors

    def _score_worker(
        self,
        ticket: TicketLike,
        worker: WorkerCandidate,
        required_skills: list[str],
    ) -> WorkerScore:
        if ticket.type == PERSON_TRAPPED:
            return self._score_emergency_worker(ticket, worker)
        return super()._score_worker(ticket, worker, required_skills)

    def _score_emergency_worker(
        self,
        ticket: TicketLike,
        worker: WorkerCandidate,
    ) -> WorkerScore:
        reasons: list[str] = []
        score = 0.0

        worker_skills = {skill.upper() for skill in worker.skills}
        if "ELEVATOR_EMERGENCY" in worker_skills:
            reasons.append("Elevator emergency certification matched")
            score += self._emergency_skill_weight
        else:
            reasons.append("Missing required skill: ELEVATOR_EMERGENCY")

        if worker.is_available:
            reasons.append("Available for emergency dispatch")
            score += self._emergency_availability_weight
        else:
            reasons.append("Currently unavailable")

        score += self._emergency_distance_points(ticket, worker, reasons)
        score += self._emergency_workload_points(worker, reasons)

        return WorkerScore(
            worker_id=worker.id,
            name=worker.name,
            score=round(score),
            reasons=reasons,
        )

    def _emergency_distance_points(
        self,
        ticket: TicketLike,
        worker: WorkerCandidate,
        reasons: list[str],
    ) -> float:
        coordinates = (
            ticket.latitude,
            ticket.longitude,
            worker.latitude,
            worker.longitude,
        )
        if any(value is None for value in coordinates):
            reasons.append("Distance unknown")
            return self._emergency_distance_weight / 2

        distance = haversine_km(
            ticket.latitude,  # type: ignore[arg-type]
            ticket.longitude,  # type: ignore[arg-type]
            worker.latitude,  # type: ignore[arg-type]
            worker.longitude,  # type: ignore[arg-type]
        )
        closeness = max(0.0, 1 - distance / self.max_distance_km)
        reasons.append(f"{distance:.1f} km from building")
        return self._emergency_distance_weight * closeness

    def _emergency_workload_points(
        self,
        worker: WorkerCandidate,
        reasons: list[str],
    ) -> float:
        capacity_left = max(
            0.0,
            1 - worker.active_ticket_count / self.max_active_tickets,
        )
        if worker.active_ticket_count == 0:
            reasons.append("No active emergency jobs")
        else:
            reasons.append(f"{worker.active_ticket_count} open job(s)")
        return self._emergency_workload_weight * capacity_left

    def config(self) -> dict[str, Any]:
        payload = super().config()
        payload["metadata_hint"] = {
            "buildings": BUILDINGS,
            "elevator_ids": ELEVATOR_IDS,
            "emergency_type": PERSON_TRAPPED,
        }
        return payload


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_positive_int(value: Any) -> bool:
    try:
        return int(value) >= 1
    except (TypeError, ValueError):
        return False
