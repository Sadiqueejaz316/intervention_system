"""Domain adapter contract.

Everything niche-specific (terminology, issue types, skills, validation rules,
worker ranking) lives behind this interface. Core services, models and routers
must never branch on a concrete domain.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from math import asin, cos, radians, sin, sqrt
from typing import Any, Protocol
from uuid import UUID


class TicketLike(Protocol):
    """Minimal shape a ticket must have to be ranked against workers."""

    type: str
    priority: str
    latitude: float | None
    longitude: float | None


@dataclass(slots=True)
class WorkerCandidate:
    """A worker plus the runtime facts needed to score them.

    The service layer builds these (including `active_ticket_count`, which
    requires a database query) so the adapter stays free of persistence code.
    """

    id: UUID
    name: str
    skills: list[str] = field(default_factory=list)
    is_available: bool = True
    latitude: float | None = None
    longitude: float | None = None
    active_ticket_count: int = 0


@dataclass(slots=True)
class WorkerScore:
    worker_id: UUID
    name: str
    score: int
    reasons: list[str] = field(default_factory=list)


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Great-circle distance in kilometres."""
    earth_radius_km = 6371.0

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)

    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )

    return 2 * earth_radius_km * asin(sqrt(a))


class DomainAdapter(ABC):
    """Base class every niche adapter extends."""

    domain_name: str = "Generic"
    issue_types: list[str] = []
    worker_label: str = "Worker"
    skill_vocabulary: list[str] = []

    status_transitions: dict[str, list[str]] = {}

    #: Metadata keys a ticket must carry, per issue type.
    required_metadata: dict[str, list[str]] = {}

    # Recommendation weights, summing to 100.
    skill_weight: int = 50
    availability_weight: int = 25
    distance_weight: int = 15
    workload_weight: int = 10

    #: Beyond this distance a worker scores nothing for proximity.
    max_distance_km: float = 50.0
    #: Workload at which a worker is considered saturated.
    max_active_tickets: int = 5

    @abstractmethod
    def get_required_skills(self, issue_type: str) -> list[str]:
        """Skills a worker needs to handle the given issue type."""

    def can_transition(self, current_status: str, new_status: str) -> bool:
        return new_status in self.status_transitions.get(current_status, [])

    def allowed_transitions(self, current_status: str) -> list[str]:
        return list(self.status_transitions.get(current_status, []))

    def validate_ticket(self, ticket_data: dict[str, Any]) -> list[str]:
        """Return human-readable problems; an empty list means the ticket is valid."""
        errors: list[str] = []

        issue_type = ticket_data.get("type")
        if self.issue_types and issue_type not in self.issue_types:
            errors.append(
                f"Unknown issue type '{issue_type}'. "
                f"Expected one of: {', '.join(self.issue_types)}."
            )

        metadata = ticket_data.get("metadata") or {}
        for key in self.required_metadata.get(str(issue_type), []):
            if metadata.get(key) in (None, ""):
                errors.append(f"Metadata field '{key}' is required for {issue_type}.")

        return errors

    def rank_workers(
        self,
        ticket: TicketLike,
        workers: list[WorkerCandidate],
    ) -> list[WorkerScore]:
        """Deterministically score workers for a ticket, best first."""
        required_skills = self.get_required_skills(ticket.type)

        scored = [
            self._score_worker(ticket, worker, required_skills) for worker in workers
        ]
        scored.sort(key=lambda result: (-result.score, result.name))

        return scored

    def _score_worker(
        self,
        ticket: TicketLike,
        worker: WorkerCandidate,
        required_skills: list[str],
    ) -> WorkerScore:
        reasons: list[str] = []
        score = 0.0

        score += self._skill_points(worker, required_skills, reasons)
        score += self._availability_points(worker, reasons)
        score += self._distance_points(ticket, worker, reasons)
        score += self._workload_points(worker, reasons)

        return WorkerScore(
            worker_id=worker.id,
            name=worker.name,
            score=round(score),
            reasons=reasons,
        )

    def _skill_points(
        self,
        worker: WorkerCandidate,
        required_skills: list[str],
        reasons: list[str],
    ) -> float:
        if not required_skills:
            reasons.append("No specific skill required")
            return self.skill_weight

        worker_skills = {skill.upper() for skill in worker.skills}
        matched = [skill for skill in required_skills if skill.upper() in worker_skills]

        if matched:
            reasons.append(f"Required skill matched: {', '.join(matched)}")
        else:
            reasons.append(f"Missing required skill: {', '.join(required_skills)}")

        return self.skill_weight * (len(matched) / len(required_skills))

    def _availability_points(
        self,
        worker: WorkerCandidate,
        reasons: list[str],
    ) -> float:
        if worker.is_available:
            reasons.append("Currently available")
            return self.availability_weight

        reasons.append("Currently unavailable")
        return 0.0

    def _distance_points(
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
            return self.distance_weight / 2

        distance = haversine_km(
            ticket.latitude,  # type: ignore[arg-type]
            ticket.longitude,  # type: ignore[arg-type]
            worker.latitude,  # type: ignore[arg-type]
            worker.longitude,  # type: ignore[arg-type]
        )
        closeness = max(0.0, 1 - distance / self.max_distance_km)
        reasons.append(f"{distance:.1f} km from the site")

        return self.distance_weight * closeness

    def _workload_points(
        self,
        worker: WorkerCandidate,
        reasons: list[str],
    ) -> float:
        capacity_left = max(
            0.0,
            1 - worker.active_ticket_count / self.max_active_tickets,
        )

        if worker.active_ticket_count == 0:
            reasons.append("No open jobs")
        else:
            reasons.append(f"{worker.active_ticket_count} open job(s)")

        return self.workload_weight * capacity_left

    def config(self) -> dict[str, Any]:
        """Domain description for the frontend, so no terminology is hardcoded there."""
        return {
            "domain_name": self.domain_name,
            "worker_label": self.worker_label,
            "issue_types": self.issue_types,
            "skill_vocabulary": self.skill_vocabulary,
            "status_transitions": self.status_transitions,
            "required_metadata": self.required_metadata,
            "required_skills_by_type": {
                issue_type: self.get_required_skills(issue_type)
                for issue_type in self.issue_types
            },
        }
