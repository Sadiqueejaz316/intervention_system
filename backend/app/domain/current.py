"""The domain the application currently runs as.

To pivot the whole product to a new niche, change only this file and point
`ACTIVE_DOMAIN` at another adapter.
"""

from app.domain.base import DomainAdapter
from app.domain.elevator import ElevatorDomainAdapter

ACTIVE_DOMAIN: DomainAdapter = ElevatorDomainAdapter()


def get_domain_adapter() -> DomainAdapter:
    """FastAPI dependency and service-layer accessor for the active domain."""
    return ACTIVE_DOMAIN
