from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Subquery, func, select
from sqlalchemy.orm import Session

from app.core.enums import HistoryAction, TicketStatus, UserRole
from app.core.errors import (
    ConflictError,
    DomainValidationError,
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
)
from app.domain.base import DomainAdapter, WorkerCandidate, WorkerScore
from app.models.assignment import Assignment
from app.models.ticket import EMERGENCY_ORDER, PRIORITY_ORDER, Ticket
from app.models.user import User
from app.schemas.assignment import AssignmentCreate
from app.services import history_service, notification_service

#: Statuses that still occupy a worker's attention.
ACTIVE_STATUSES = [TicketStatus.ASSIGNED.value, TicketStatus.IN_PROGRESS.value]


def current_assignments() -> Subquery:
    """Rank each ticket's assignments so rank 1 is the one in force.

    Reassignment appends rows, so "who is on this job" is always the newest row.
    """
    return select(
        Assignment.id.label("assignment_id"),
        Assignment.ticket_id,
        Assignment.contractor_id,
        func.row_number()
        .over(
            partition_by=Assignment.ticket_id,
            order_by=Assignment.assigned_at.desc(),
        )
        .label("rank"),
    ).subquery()


def get_active_assignment(db: Session, ticket_id: UUID) -> Assignment | None:
    """The assignment currently in force for a ticket, or None if never assigned."""
    query = (
        select(Assignment)
        .where(Assignment.ticket_id == ticket_id)
        .order_by(Assignment.assigned_at.desc())
        .limit(1)
    )

    return db.execute(query).scalars().first()


def current_workers_for(db: Session, ticket_ids: list[UUID]) -> dict[UUID, User]:
    """Map ticket id -> worker on the job, for rendering queues in one query."""
    if not ticket_ids:
        return {}

    current = current_assignments()
    query = (
        select(current.c.ticket_id, User)
        .join(User, User.id == current.c.contractor_id)
        .where(current.c.rank == 1, current.c.ticket_id.in_(ticket_ids))
    )

    return dict(db.execute(query).all())  # type: ignore[arg-type]


def workload_by_worker(db: Session) -> dict[UUID, int]:
    """Count of unfinished jobs each worker currently holds."""
    current = current_assignments()
    query = (
        select(current.c.contractor_id, func.count(Ticket.id))
        .join(Ticket, Ticket.id == current.c.ticket_id)
        .where(current.c.rank == 1, Ticket.status.in_(ACTIVE_STATUSES))
        .group_by(current.c.contractor_id)
    )

    return dict(db.execute(query).all())  # type: ignore[arg-type]


def list_workers(
    db: Session,
    *,
    available: bool | None = None,
    skill: str | None = None,
) -> list[User]:
    query = select(User).where(User.role == UserRole.CONTRACTOR.value)

    if available is not None:
        query = query.where(User.is_available.is_(available))
    if skill is not None:
        query = query.where(User.skills.contains([skill.upper()]))

    return list(db.execute(query.order_by(User.name)).scalars().all())


def get_worker(db: Session, worker_id: UUID, adapter: DomainAdapter) -> User:
    worker = db.get(User, worker_id)
    if worker is None:
        raise NotFoundError(f"User {worker_id} does not exist.")

    if worker.role != UserRole.CONTRACTOR:
        raise DomainValidationError(
            f"{worker.name} is a {worker.role}, not a {adapter.worker_label}."
        )

    return worker


def list_worker_tickets(
    db: Session,
    worker_id: UUID,
    *,
    active_only: bool = False,
) -> list[Ticket]:
    """Jobs the worker currently holds, most urgent first."""
    current = current_assignments()
    query = (
        select(Ticket)
        .join(current, current.c.ticket_id == Ticket.id)
        .where(current.c.rank == 1, current.c.contractor_id == worker_id)
    )

    if active_only:
        query = query.where(Ticket.status.in_(ACTIVE_STATUSES))

    query = query.order_by(EMERGENCY_ORDER, PRIORITY_ORDER, Ticket.created_at)

    return list(db.execute(query).scalars().all())


def recommend_workers(
    db: Session,
    ticket_id: UUID,
    adapter: DomainAdapter,
    *,
    limit: int = 5,
) -> list[WorkerScore]:
    """Deterministic worker suggestions; the ranking rules belong to the domain."""
    ticket = load_ticket(db, ticket_id)
    workload = workload_by_worker(db)

    candidates = [
        WorkerCandidate(
            id=worker.id,
            name=worker.name,
            skills=list(worker.skills or []),
            is_available=worker.is_available,
            latitude=worker.latitude,
            longitude=worker.longitude,
            active_ticket_count=workload.get(worker.id, 0),
        )
        for worker in list_workers(db)
    ]

    return adapter.rank_workers(ticket, candidates)[:limit]


def assign_ticket(
    db: Session,
    ticket_id: UUID,
    data: AssignmentCreate,
    adapter: DomainAdapter,
    *,
    actor: User,
) -> Assignment:
    """Dispatch a ticket to a worker.

    Assignment, status change, history and notifications share one transaction.
    Reassignment appends a row, so earlier dispatch attempts stay auditable.
    `actor` is the authenticated dispatcher, so `assigned_by` cannot be spoofed.
    """
    ticket = load_ticket(db, ticket_id)
    worker = get_worker(db, data.contractor_id, adapter)

    previous = get_active_assignment(db, ticket_id)
    previous_worker_id = previous.contractor_id if previous is not None else None

    if previous_worker_id == worker.id:
        raise ConflictError(f"'{ticket.title}' is already assigned to {worker.name}.")

    _guard_assignable(ticket, adapter)

    try:
        assignment = Assignment(
            ticket_id=ticket.id,
            contractor_id=worker.id,
            assigned_by=actor.id,
            notes=data.notes,
        )
        db.add(assignment)

        old_status = ticket.status
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.ASSIGNED.value

        metadata: dict[str, str] = {"contractor_id": str(worker.id)}
        if previous_worker_id is not None:
            metadata["reassigned_from"] = str(previous_worker_id)

        history_service.record(
            db,
            ticket_id=ticket.id,
            action=HistoryAction.ASSIGNED,
            user_id=actor.id,
            old_status=old_status,
            new_status=ticket.status,
            comment=f"Assigned to {worker.name}",
            metadata=metadata,
        )

        notification_service.notify_assignment(
            db,
            ticket=ticket,
            worker=worker,
            previous_worker_id=previous_worker_id,
            actor_id=actor.id,
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(assignment)

    return assignment


def accept_assignment(
    db: Session,
    ticket_id: UUID,
    adapter: DomainAdapter,
    *,
    actor: User,
) -> Assignment:
    """The worker confirms they are taking the job; the status is unchanged."""
    ticket = load_ticket(db, ticket_id)
    assignment = get_active_assignment(db, ticket_id)

    if assignment is None:
        raise ConflictError(f"'{ticket.title}' has not been assigned to anyone yet.")
    if assignment.accepted_at is not None:
        raise ConflictError("This assignment has already been accepted.")

    # Ownership: the job belongs to one worker, whoever holds the token.
    if actor.role != UserRole.ADMIN and actor.id != assignment.contractor_id:
        raise PermissionDeniedError(
            f"Only the assigned {adapter.worker_label} can accept this job."
        )

    worker = db.get(User, assignment.contractor_id)
    if worker is None:
        raise NotFoundError(f"User {assignment.contractor_id} does not exist.")

    try:
        assignment.accepted_at = datetime.now(UTC)

        history_service.record(
            db,
            ticket_id=ticket.id,
            action=HistoryAction.ASSIGNMENT_ACCEPTED,
            user_id=worker.id,
            old_status=ticket.status,
            new_status=ticket.status,
            comment=f"{worker.name} accepted the job",
        )

        notification_service.notify_assignment_accepted(
            db,
            ticket=ticket,
            worker=worker,
            assigned_by=assignment.assigned_by,
            actor_id=actor.id,
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(assignment)

    return assignment


def sync_with_ticket_status(
    db: Session,
    ticket_id: UUID,
    new_status: str,
) -> None:
    """Keep the assignment timeline in step with the ticket status."""
    assignment = get_active_assignment(db, ticket_id)
    if assignment is None:
        return

    now = datetime.now(UTC)

    if new_status == TicketStatus.IN_PROGRESS:
        # Starting work implies acceptance, even if ACCEPT was never pressed.
        if assignment.accepted_at is None:
            assignment.accepted_at = now
        if assignment.started_at is None:
            assignment.started_at = now
    elif new_status == TicketStatus.RESOLVED and assignment.completed_at is None:
        assignment.completed_at = now


def load_ticket(db: Session, ticket_id: UUID) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found.")

    return ticket


def _guard_assignable(ticket: Ticket, adapter: DomainAdapter) -> None:
    if ticket.status == TicketStatus.OPEN:
        if not adapter.can_transition(TicketStatus.OPEN, TicketStatus.ASSIGNED):
            raise InvalidTransitionError(
                f"The {adapter.domain_name} workflow does not allow "
                f"{TicketStatus.OPEN} tickets to be assigned."
            )
        return

    # Reassignment leaves the status alone, so no transition is involved.
    if ticket.status == TicketStatus.ASSIGNED:
        return

    raise ConflictError(
        f"Cannot assign a ticket that is {ticket.status}. "
        f"Assignment is only possible while a ticket is "
        f"{TicketStatus.OPEN} or {TicketStatus.ASSIGNED}."
    )
