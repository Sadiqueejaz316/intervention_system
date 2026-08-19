from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth import access
from app.auth.dependencies import CurrentUser, DbSession, require_roles
from app.core.enums import UserRole
from app.domain.base import DomainAdapter
from app.domain.current import get_domain_adapter
from app.models.user import User
from app.schemas.ticket import TicketRead
from app.schemas.user import WorkerRead
from app.services import assignment_service

router = APIRouter(prefix="/workers", tags=["Workers"])

Domain = Annotated[DomainAdapter, Depends(get_domain_adapter)]
Dispatcher = Annotated[User, Depends(require_roles(UserRole.DISPATCHER))]


@router.get(
    "",
    response_model=list[WorkerRead],
    summary="Workers available to the dispatcher",
)
def list_workers(
    db: DbSession,
    current_user: Dispatcher,
    available: bool | None = None,
    skill: str | None = None,
) -> list[WorkerRead]:
    """Dispatch-only: a contractor has no reason to enumerate their colleagues."""
    workers = assignment_service.list_workers(db, available=available, skill=skill)
    workload = assignment_service.workload_by_worker(db)

    return [
        WorkerRead.from_user(worker, workload.get(worker.id, 0)) for worker in workers
    ]


# Declared before /{worker_id}/... so that "me" is not parsed as a worker id.
@router.get(
    "/me",
    response_model=WorkerRead,
    summary="Your own worker profile",
)
def get_my_worker_profile(
    db: DbSession,
    adapter: Domain,
    current_user: CurrentUser,
) -> WorkerRead:
    worker = assignment_service.get_worker(db, current_user.id, adapter)
    workload = assignment_service.workload_by_worker(db)

    return WorkerRead.from_user(worker, workload.get(worker.id, 0))


@router.get(
    "/me/tickets",
    response_model=list[TicketRead],
    summary="Your own jobs",
)
def list_my_tickets(
    db: DbSession,
    adapter: Domain,
    current_user: CurrentUser,
    active_only: bool = False,
) -> list[TicketRead]:
    return list_worker_tickets(
        current_user.id,
        db,
        adapter,
        current_user,
        active_only=active_only,
    )


@router.get(
    "/{worker_id}/tickets",
    response_model=list[TicketRead],
    summary="Jobs currently held by a worker",
)
def list_worker_tickets(
    worker_id: UUID,
    db: DbSession,
    adapter: Domain,
    current_user: CurrentUser,
    active_only: bool = False,
) -> list[TicketRead]:
    """A contractor may only ask about their own jobs; staff may ask about anyone's."""
    access.ensure_can_view_worker(worker_id, current_user)

    worker = assignment_service.get_worker(db, worker_id, adapter)
    tickets = assignment_service.list_worker_tickets(
        db,
        worker_id,
        active_only=active_only,
    )

    return [TicketRead.from_ticket(ticket, worker) for ticket in tickets]
