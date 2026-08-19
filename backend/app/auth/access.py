"""Per-resource authorization: may *this* user touch *this* ticket?

Role checks that need nothing but the user belong in `require_roles`. Everything
here needs the resource as well — who reported the ticket, who holds it now — so
it runs in the router once the resource is known, before the service is asked to
change anything.

This module answers "is it allowed?" only. It never decides what a valid
transition is (that is the domain adapter) nor how the change is applied (that is
the service layer).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import TicketStatus, UserRole
from app.core.errors import PermissionDeniedError
from app.models.assignment import Assignment
from app.models.ticket import Ticket
from app.models.user import User

#: Roles that see and steer the whole queue.
STAFF_ROLES = (UserRole.DISPATCHER, UserRole.ADMIN)

#: Statuses only the contractor holding the job may set.
_CONTRACTOR_ONLY_STATUSES = (TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED)


def is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def current_contractor_id(db: Session, ticket_id: UUID) -> UUID | None:
    """Who holds the job right now: the newest assignment wins."""
    query = (
        select(Assignment.contractor_id)
        .where(Assignment.ticket_id == ticket_id)
        .order_by(Assignment.assigned_at.desc())
        .limit(1)
    )

    return db.execute(query).scalars().first()


def _has_ever_been_assigned(db: Session, ticket_id: UUID, user_id: UUID) -> bool:
    """Contractors keep read access to jobs they were once given, for their record."""
    query = select(Assignment.id).where(
        Assignment.ticket_id == ticket_id,
        Assignment.contractor_id == user_id,
    )

    return db.execute(query).scalars().first() is not None


def can_view_ticket(db: Session, ticket: Ticket, user: User) -> bool:
    if is_staff(user):
        return True
    if ticket.reporter_id is not None and ticket.reporter_id == user.id:
        return True
    if user.role == UserRole.CONTRACTOR:
        return _has_ever_been_assigned(db, ticket.id, user.id)

    return False


def ensure_can_view_ticket(db: Session, ticket: Ticket, user: User) -> None:
    if not can_view_ticket(db, ticket, user):
        raise PermissionDeniedError("You do not have access to this ticket.")


def ensure_holds_assignment(db: Session, ticket: Ticket, user: User, action: str) -> None:
    """Only the contractor currently on the job may act on it."""
    if is_admin(user):
        return

    if current_contractor_id(db, ticket.id) != user.id:
        raise PermissionDeniedError(
            f"Only the contractor assigned to this ticket can {action} it."
        )


def ensure_can_change_status(
    db: Session,
    ticket: Ticket,
    user: User,
    new_status: TicketStatus,
) -> None:
    """Gate the generic status endpoint by target status.

    Whether the move itself is legal is still the domain adapter's call; this
    only decides who is entitled to attempt it, so no role can walk a ticket
    through a step that belongs to somebody else.
    """
    if is_admin(user):
        return

    if new_status in _CONTRACTOR_ONLY_STATUSES:
        ensure_holds_assignment(
            db,
            ticket,
            user,
            "start work on" if new_status == TicketStatus.IN_PROGRESS else "resolve",
        )
        return

    # CLOSED, and the moves the workflow refuses anyway, are dispatcher business.
    if not is_staff(user):
        raise PermissionDeniedError(
            f"Only a {UserRole.DISPATCHER} or {UserRole.ADMIN} "
            f"can move a ticket to {new_status}."
        )


def ensure_owns_notification(user_id: UUID, user: User) -> None:
    if user_id != user.id:
        raise PermissionDeniedError("You do not have access to this notification.")


def ensure_can_view_worker(worker_id: UUID, user: User) -> None:
    """Contractors may look at their own record; only staff may look at anyone's."""
    if is_staff(user) or worker_id == user.id:
        return

    raise PermissionDeniedError("You can only view your own worker profile.")
