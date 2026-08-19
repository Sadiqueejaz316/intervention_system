"""The domain the application currently runs as.

To pivot the whole product to a new niche, change only this file: either edit
`CurrentDomainAdapter` or point `ACTIVE_DOMAIN` at another adapter, for example
`MunicipalMaintenanceAdapter` from `app.domain.examples`.
"""

from app.core.enums import TicketStatus
from app.domain.base import DomainAdapter


class CurrentDomainAdapter(DomainAdapter):
    domain_name = "Generic Intervention"

    issue_types = [
        "GENERAL",
        "EQUIPMENT",
        "DAMAGE",
        "OUTAGE",
    ]

    worker_label = "Contractor"

    skill_vocabulary = [
        "GENERAL",
        "MECHANICAL",
        "ELECTRICAL",
        "EMERGENCY",
    ]

    status_transitions = {
        TicketStatus.OPEN: [TicketStatus.ASSIGNED],
        TicketStatus.ASSIGNED: [TicketStatus.IN_PROGRESS],
        TicketStatus.IN_PROGRESS: [TicketStatus.RESOLVED],
        TicketStatus.RESOLVED: [TicketStatus.CLOSED],
        TicketStatus.CLOSED: [],
    }

    required_metadata: dict[str, list[str]] = {}

    _skills_by_type = {
        "GENERAL": [],
        "EQUIPMENT": ["MECHANICAL"],
        "DAMAGE": ["GENERAL"],
        "OUTAGE": ["ELECTRICAL"],
    }

    def get_required_skills(self, issue_type: str) -> list[str]:
        return list(self._skills_by_type.get(issue_type, []))


ACTIVE_DOMAIN: DomainAdapter = CurrentDomainAdapter()


def get_domain_adapter() -> DomainAdapter:
    """FastAPI dependency and service-layer accessor for the active domain."""
    return ACTIVE_DOMAIN
