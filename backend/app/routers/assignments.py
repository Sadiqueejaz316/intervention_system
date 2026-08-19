from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import DbSession, require_roles
from app.core.enums import UserRole
from app.domain.base import DomainAdapter
from app.domain.current import get_domain_adapter
from app.models.user import User
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentRead,
    WorkerRecommendation,
)
from app.services import assignment_service

router = APIRouter(prefix="/tickets", tags=["Assignments"])

Domain = Annotated[DomainAdapter, Depends(get_domain_adapter)]
Dispatcher = Annotated[User, Depends(require_roles(UserRole.DISPATCHER))]
Contractor = Annotated[User, Depends(require_roles(UserRole.CONTRACTOR))]


@router.get(
    "/{ticket_id}/recommendations",
    response_model=list[WorkerRecommendation],
    summary="Ranked worker suggestions for a ticket",
)
def recommend_workers(
    ticket_id: UUID,
    db: DbSession,
    adapter: Domain,
    current_user: Dispatcher,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[WorkerRecommendation]:
    """Dispatch-only: the ranking exposes every worker's skills and workload."""
    ranked = assignment_service.recommend_workers(db, ticket_id, adapter, limit=limit)

    return [WorkerRecommendation.model_validate(result) for result in ranked]


@router.post(
    "/{ticket_id}/assign",
    response_model=AssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a ticket to a worker",
)
def assign_ticket(
    ticket_id: UUID,
    data: AssignmentCreate,
    db: DbSession,
    adapter: Domain,
    current_user: Dispatcher,
) -> AssignmentRead:
    assignment = assignment_service.assign_ticket(
        db,
        ticket_id,
        data,
        adapter,
        actor=current_user,
    )

    return AssignmentRead.model_validate(assignment)


@router.post(
    "/{ticket_id}/accept",
    response_model=AssignmentRead,
    summary="Worker accepts the assigned job",
)
def accept_assignment(
    ticket_id: UUID,
    db: DbSession,
    adapter: Domain,
    current_user: Contractor,
) -> AssignmentRead:
    """The role gate is here; that it is *this* worker's job is checked in the
    service, where the assignment is loaded."""
    assignment = assignment_service.accept_assignment(
        db,
        ticket_id,
        adapter,
        actor=current_user,
    )

    return AssignmentRead.model_validate(assignment)
