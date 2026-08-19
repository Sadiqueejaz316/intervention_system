from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.enums import HistoryAction, TicketStatus
from app.core.errors import (
    ConflictError,
    DomainValidationError,
    InvalidTransitionError,
    NotFoundError,
)
from app.domain.base import DomainAdapter
from app.models.ticket import PRIORITY_ORDER, Ticket
from app.models.ticket_history import TicketHistory
from app.schemas.ticket import TicketCreate, TicketStatusUpdate
from app.services import assignment_service, history_service, notification_service

# A plain STATUS_CHANGED entry is correct but vague; these read better in the
# timeline the field and dispatcher views render.
_ACTION_BY_STATUS = {
    TicketStatus.IN_PROGRESS: HistoryAction.WORK_STARTED,
    TicketStatus.RESOLVED: HistoryAction.RESOLVED,
    TicketStatus.CLOSED: HistoryAction.CLOSED,
}


def create_ticket(
    db: Session,
    data: TicketCreate,
    adapter: DomainAdapter,
    *,
    reporter_id: UUID,
) -> Ticket:
    """Validate against the active domain, then persist ticket + history atomically.

    `reporter_id` comes from the authenticated caller, never from the payload.
    """
    errors = adapter.validate_ticket(data.model_dump(mode="json"))
    if errors:
        raise DomainValidationError(" ".join(errors))

    ticket = Ticket(
        title=data.title,
        description=data.description,
        type=data.type,
        priority=data.priority.value,
        status=TicketStatus.OPEN.value,
        reporter_id=reporter_id,
        location_text=data.location_text,
        latitude=data.latitude,
        longitude=data.longitude,
        meta=data.metadata,
    )

    try:
        db.add(ticket)
        db.flush()

        history_service.record(
            db,
            ticket_id=ticket.id,
            action=HistoryAction.TICKET_CREATED,
            user_id=reporter_id,
            new_status=TicketStatus.OPEN.value,
            comment="Ticket created",
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(ticket)

    return ticket


def get_ticket(db: Session, ticket_id: UUID) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found.")

    return ticket


def change_status(
    db: Session,
    ticket_id: UUID,
    data: TicketStatusUpdate,
    adapter: DomainAdapter,
    *,
    actor_id: UUID,
) -> Ticket:
    """Move a ticket through the workflow.

    The transition is validated by the active domain adapter; the ticket update,
    the history entry and the notifications all share one transaction, so a
    ticket can never change status without leaving a trail. `actor_id` is the
    authenticated caller, so the timeline records who really did it.
    """
    ticket = get_ticket(db, ticket_id)
    old_status = ticket.status
    new_status = data.status.value

    _guard_transition(adapter, old_status, new_status)

    assignment = assignment_service.get_active_assignment(db, ticket_id)

    try:
        ticket.status = new_status
        assignment_service.sync_with_ticket_status(db, ticket_id, new_status)

        history_service.record(
            db,
            ticket_id=ticket.id,
            action=_ACTION_BY_STATUS.get(new_status, HistoryAction.STATUS_CHANGED),
            user_id=actor_id,
            old_status=old_status,
            new_status=new_status,
            comment=data.comment,
        )

        notification_service.notify_status_change(
            db,
            ticket=ticket,
            old_status=old_status,
            new_status=new_status,
            actor_id=actor_id,
            worker_id=assignment.contractor_id if assignment is not None else None,
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(ticket)

    return ticket


def _guard_transition(
    adapter: DomainAdapter,
    old_status: str,
    new_status: str,
) -> None:
    if new_status == old_status:
        raise ConflictError(f"Ticket is already {old_status}.")

    if not adapter.can_transition(old_status, new_status):
        allowed = adapter.allowed_transitions(old_status)
        expected = ", ".join(allowed) if allowed else "no further transitions"
        raise InvalidTransitionError(
            f"Cannot move a ticket from {old_status} to {new_status}. "
            f"Allowed from {old_status}: {expected}."
        )

    # Reaching ASSIGNED without an assignment row would leave the ticket
    # assigned to nobody, so that step belongs to the assign endpoint.
    if new_status == TicketStatus.ASSIGNED:
        raise ConflictError(
            "Assign the ticket through POST /tickets/{ticket_id}/assign "
            "so the assignment is recorded."
        )


def list_history(db: Session, ticket_id: UUID) -> list[TicketHistory]:
    get_ticket(db, ticket_id)

    return history_service.list_for_ticket(db, ticket_id)


def list_tickets(
    db: Session,
    *,
    status: str | None = None,
    priority: str | None = None,
    type: str | None = None,
    reporter_id: UUID | None = None,
    assigned_to: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Ticket]:
    """Queue order: most urgent first, then oldest first within a priority."""
    query: Select[tuple[Ticket]] = select(Ticket)

    if status is not None:
        query = query.where(Ticket.status == status)
    if priority is not None:
        query = query.where(Ticket.priority == priority)
    if type is not None:
        query = query.where(Ticket.type == type)
    if reporter_id is not None:
        query = query.where(Ticket.reporter_id == reporter_id)
    if assigned_to is not None:
        # The job belongs to whoever holds the newest assignment, so an earlier
        # worker stops seeing a ticket the moment it is reassigned.
        current = assignment_service.current_assignments()
        query = query.join(current, current.c.ticket_id == Ticket.id).where(
            current.c.rank == 1,
            current.c.contractor_id == assigned_to,
        )

    query = query.order_by(PRIORITY_ORDER, Ticket.created_at).limit(limit).offset(offset)

    return list(db.execute(query).scalars().all())
