from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.enums import TicketPriority, TicketStatus
from app.domain.base import DomainAdapter
from app.domain.current import get_domain_adapter
from app.schemas.domain import DomainConfigResponse

router = APIRouter(prefix="/domain", tags=["Domain"])

Domain = Annotated[DomainAdapter, Depends(get_domain_adapter)]


@router.get(
    "/config",
    response_model=DomainConfigResponse,
    summary="Terminology and rules of the active domain",
)
def get_config(adapter: Domain) -> DomainConfigResponse:
    return DomainConfigResponse(
        **adapter.config(),
        priorities=[priority.value for priority in TicketPriority],
        statuses=[status.value for status in TicketStatus],
    )


@router.get(
    "/issue-types",
    response_model=list[str],
    summary="Issue types accepted by the active domain",
)
def get_issue_types(adapter: Domain) -> list[str]:
    return adapter.issue_types
