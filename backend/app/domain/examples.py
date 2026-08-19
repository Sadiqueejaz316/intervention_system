"""Reference adapter showing how a real niche plugs in.

This is an EXAMPLE, not the production domain. Nothing imports it. It exists to
demonstrate that switching niches requires no schema or service changes: only
issue types, skills, terminology and validation rules move.

To activate it, edit `app/domain/current.py`:

    from app.domain.examples import MunicipalMaintenanceAdapter

    ACTIVE_DOMAIN: DomainAdapter = MunicipalMaintenanceAdapter()
"""

from app.core.enums import TicketStatus
from app.domain.base import DomainAdapter


class MunicipalMaintenanceAdapter(DomainAdapter):
    domain_name = "Municipal Maintenance"

    issue_types = [
        "ROAD_DAMAGE",
        "STREET_LIGHT",
        "WATER_LEAK",
        "BLOCKED_ROAD",
        "DAMAGED_SIGN",
    ]

    worker_label = "Field Crew"

    skill_vocabulary = [
        "ROAD_REPAIR",
        "ELECTRICAL",
        "PLUMBING",
        "SIGN_REPAIR",
    ]

    status_transitions = {
        TicketStatus.OPEN: [TicketStatus.ASSIGNED],
        TicketStatus.ASSIGNED: [TicketStatus.IN_PROGRESS],
        TicketStatus.IN_PROGRESS: [TicketStatus.RESOLVED],
        TicketStatus.RESOLVED: [TicketStatus.CLOSED],
        TicketStatus.CLOSED: [],
    }

    # Niche-specific intake rules, enforced without touching the tickets table
    # because they live in the JSONB metadata column.
    required_metadata = {
        "ROAD_DAMAGE": ["road_segment"],
        "BLOCKED_ROAD": ["road_segment", "hazard"],
    }

    _skills_by_type = {
        "ROAD_DAMAGE": ["ROAD_REPAIR"],
        "STREET_LIGHT": ["ELECTRICAL"],
        "WATER_LEAK": ["PLUMBING"],
        "BLOCKED_ROAD": ["ROAD_REPAIR"],
        "DAMAGED_SIGN": ["SIGN_REPAIR"],
    }

    def get_required_skills(self, issue_type: str) -> list[str]:
        return list(self._skills_by_type.get(issue_type, []))
