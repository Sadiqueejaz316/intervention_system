from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth import access
from app.auth.dependencies import CurrentUser, DbSession
from app.core.enums import TicketPriority, TicketStatus, UserRole
from app.domain.base import DomainAdapter
from app.domain.current import get_domain_adapter
from app.models.user import User
from app.schemas.ticket import (
    TicketCreate,
    TicketHistoryRead,
    TicketRead,
    TicketStats,
    TicketStatusUpdate,
)
from app.services import assignment_service, ticket_service

router = APIRouter(prefix="/tickets", tags=["Tickets"])

Domain = Annotated[DomainAdapter, Depends(get_domain_adapter)]


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Report a new issue",
)
def create_ticket(
    data: TicketCreate,
    db: DbSession,
    adapter: Domain,
    current_user: CurrentUser,
) -> TicketRead:
    """The reporter is the authenticated caller, never a field in the payload."""
    ticket = ticket_service.create_ticket(
        db,
        data,
        adapter,
        reporter_id=current_user.id,
    )

    return TicketRead.model_validate(ticket)


@router.get(
    "",
    response_model=list[TicketRead],
    summary="List tickets, highest priority first",
)
def list_tickets(
    db: DbSession,
    current_user: CurrentUser,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    type: str | None = None,
    reporter_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TicketRead]:
    """The queue each role is entitled to see.

    Dispatchers and admins get everything; a reporter gets their own reports and
    a contractor their own jobs, whatever the query string asks for.
    """
    scope = _visible_scope(current_user, reporter_id)

    tickets = ticket_service.list_tickets(
        db,
        status=status.value if status else None,
        priority=priority.value if priority else None,
        type=type,
        limit=limit,
        offset=offset,
        **scope,
    )
    workers = assignment_service.current_workers_for(
        db,
        [ticket.id for ticket in tickets],
    )

    return [
        TicketRead.from_ticket(ticket, workers.get(ticket.id)) for ticket in tickets
    ]


@router.get(
    "/stats",
    response_model=TicketStats,
    summary="Operations counts for the signed-in role",
)
def get_ticket_stats(db: DbSession, current_user: CurrentUser) -> TicketStats:
    scope = _visible_scope(current_user, reporter_id=None)
    return TicketStats(**ticket_service.ticket_stats(db, **scope))


@router.get(
    "/{ticket_id}",
    response_model=TicketRead,
    summary="Fetch a single ticket",
)
def get_ticket(
    ticket_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> TicketRead:
    ticket = ticket_service.get_ticket(db, ticket_id)
    access.ensure_can_view_ticket(db, ticket, current_user)

    assignment = assignment_service.get_active_assignment(db, ticket_id)

    return TicketRead.from_ticket(
        ticket,
        assignment.contractor if assignment is not None else None,
    )


@router.patch(
    "/{ticket_id}/status",
    response_model=TicketRead,
    summary="Move a ticket through the workflow",
)
def update_ticket_status(
    ticket_id: UUID,
    data: TicketStatusUpdate,
    db: DbSession,
    adapter: Domain,
    current_user: CurrentUser,
) -> TicketRead:
    """Who may attempt the move is settled here; whether the move is legal is the
    adapter's call, inside the service."""
    ticket = ticket_service.get_ticket(db, ticket_id)
    access.ensure_can_change_status(db, ticket, current_user, data.status)

    ticket = ticket_service.change_status(
        db,
        ticket_id,
        data,
        adapter,
        actor_id=current_user.id,
    )
    assignment = assignment_service.get_active_assignment(db, ticket_id)

    return TicketRead.from_ticket(
        ticket,
        assignment.contractor if assignment is not None else None,
    )


@router.get(
    "/{ticket_id}/history",
    response_model=list[TicketHistoryRead],
    summary="Ticket timeline, oldest first",
)
def get_ticket_history(
    ticket_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> list[TicketHistoryRead]:
    ticket = ticket_service.get_ticket(db, ticket_id)
    access.ensure_can_view_ticket(db, ticket, current_user)

    entries = ticket_service.list_history(db, ticket_id)

    return [TicketHistoryRead.model_validate(entry) for entry in entries]


def _visible_scope(
    current_user: User,
    reporter_id: UUID | None,
) -> dict[str, UUID | None]:
    """Narrow the queue filters to what this role is allowed to ask for."""
    if access.is_staff(current_user):
        return {"reporter_id": reporter_id}

    if current_user.role == UserRole.CONTRACTOR:
        return {"assigned_to": current_user.id}

    return {"reporter_id": current_user.id}
