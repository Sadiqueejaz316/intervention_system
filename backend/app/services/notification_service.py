"""In-app notifications.

This module deliberately depends on nothing but the models, so any service can
use it without creating an import cycle. Callers pass in whoever is involved.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import NotificationType, TicketStatus, UserRole
from app.core.errors import NotFoundError
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.models.user import User


def create_notification(
    db: Session,
    *,
    user_id: UUID,
    title: str,
    message: str,
    ticket_id: UUID | None = None,
    type: NotificationType = NotificationType.INFO,
) -> Notification:
    """Add an in-app notification to the caller's transaction. The caller commits."""
    notification = Notification(
        user_id=user_id,
        ticket_id=ticket_id,
        title=title,
        message=message,
        type=type.value,
    )
    db.add(notification)

    return notification


def notify_new_ticket(
    db: Session,
    *,
    ticket: Ticket,
    actor_id: UUID | None,
) -> list[Notification]:
    """Dispatchers hear about a new emergency immediately. Ordinary reports wait."""
    if not _is_emergency(ticket):
        return []

    planned = [
        (
            dispatcher_id,
            "🚨 EMERGENCY: person trapped",
            _emergency_message(ticket),
            NotificationType.ESCALATION,
        )
        for dispatcher_id in dispatcher_ids(db)
    ]

    return _dispatch(db, ticket, planned, actor_id)


def notify_status_change(
    db: Session,
    *,
    ticket: Ticket,
    old_status: str,
    new_status: str,
    actor_id: UUID | None,
    worker_id: UUID | None,
) -> list[Notification]:
    """Tell everyone following the ticket, except whoever made the change."""
    recipients: set[UUID | None] = {ticket.reporter_id, worker_id}

    # A resolved ticket is waiting on a dispatcher to close it.
    if new_status == TicketStatus.RESOLVED:
        recipients.update(dispatcher_ids(db))

    recipients -= {None, actor_id}

    return [
        create_notification(
            db,
            user_id=recipient,  # type: ignore[arg-type]
            ticket_id=ticket.id,
            title=f"Ticket moved to {new_status}",
            message=f"'{ticket.title}' moved from {old_status} to {new_status}.",
            type=NotificationType.STATUS_CHANGE,
        )
        for recipient in sorted(recipients, key=str)
    ]


def notify_assignment(
    db: Session,
    *,
    ticket: Ticket,
    worker: User,
    previous_worker_id: UUID | None,
    actor_id: UUID | None,
) -> list[Notification]:
    """Alert the new worker, anyone replaced, and the reporter."""
    location = _incident_where(ticket)
    emergency = _is_emergency(ticket)
    worker_title = (
        f"🚨 EMERGENCY job: {ticket.title}" if emergency else f"New job: {ticket.title}"
    )
    worker_message = (
        _emergency_message(ticket)
        if emergency
        else (
            f"You have been assigned a {ticket.priority} priority "
            f"{ticket.type} job at {location}."
        )
    )

    planned: list[tuple[UUID | None, str, str, NotificationType]] = [
        (
            worker.id,
            worker_title,
            worker_message,
            NotificationType.ESCALATION if emergency else NotificationType.ASSIGNMENT,
        ),
        (
            previous_worker_id,
            "Job reassigned",
            f"'{ticket.title}' has been reassigned to {worker.name}.",
            NotificationType.INFO,
        ),
        (
            ticket.reporter_id,
            "Your report is being handled",
            f"'{ticket.title}' was assigned to {worker.name}.",
            NotificationType.INFO,
        ),
    ]

    return _dispatch(db, ticket, planned, actor_id)


def notify_assignment_accepted(
    db: Session,
    *,
    ticket: Ticket,
    worker: User,
    assigned_by: UUID | None,
    actor_id: UUID | None,
) -> list[Notification]:
    """Let the dispatcher know the job was picked up."""
    followers = [assigned_by] if assigned_by is not None else dispatcher_ids(db)

    planned = [
        (
            follower,
            "Assignment accepted",
            f"{worker.name} accepted '{ticket.title}'.",
            NotificationType.ASSIGNMENT,
        )
        for follower in followers
    ]

    return _dispatch(db, ticket, planned, actor_id)


def _dispatch(
    db: Session,
    ticket: Ticket,
    planned: list[tuple[UUID | None, str, str, NotificationType]],
    actor_id: UUID | None,
) -> list[Notification]:
    """Send each planned notification once, skipping the actor's own actions."""
    created: list[Notification] = []
    already_notified: set[UUID | None] = {None, actor_id}

    for user_id, title, message, notification_type in planned:
        if user_id in already_notified:
            continue

        already_notified.add(user_id)
        created.append(
            create_notification(
                db,
                user_id=user_id,  # type: ignore[arg-type]
                ticket_id=ticket.id,
                title=title,
                message=message,
                type=notification_type,
            )
        )

    return created


def list_for_user(
    db: Session,
    user_id: UUID,
    *,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    """One user's inbox, newest first.

    The recipient is always the authenticated caller: this query is the only way
    notifications are read, so nobody can ask for somebody else's inbox.
    """
    query = select(Notification).where(Notification.user_id == user_id)

    if unread_only:
        query = query.where(Notification.is_read.is_(False))

    query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)

    return list(db.execute(query).scalars().all())


def unread_count(db: Session, user_id: UUID) -> int:
    query = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )

    return db.execute(query).scalar_one()


def get_notification(db: Session, notification_id: UUID) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise NotFoundError(f"Notification {notification_id} not found.")

    return notification


def mark_read(db: Session, notification: Notification) -> Notification:
    """Idempotent: marking an already-read notification is not an error."""
    if not notification.is_read:
        try:
            notification.is_read = True
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(notification)

    return notification


def dispatcher_ids(db: Session) -> list[UUID]:
    query = select(User.id).where(User.role == UserRole.DISPATCHER.value)

    return list(db.execute(query).scalars().all())


def _is_emergency(ticket: Ticket) -> bool:
    return bool(ticket.meta.get("is_emergency"))


def _incident_where(ticket: Ticket) -> str:
    meta = ticket.meta or {}
    building = meta.get("building_name")
    elevator = meta.get("elevator_id")
    if building and elevator:
        return f"{building} — {elevator}"
    return ticket.location_text or "an unspecified location"


def _emergency_message(ticket: Ticket) -> str:
    meta = ticket.meta or {}
    people = meta.get("people_trapped")
    elevator = meta.get("elevator_id") or "the elevator"
    building = meta.get("building_name") or "the building"
    people_bit = f"{people} people" if people else "People"
    return f"🚨 EMERGENCY: {people_bit} trapped in elevator {elevator} at {building}."
