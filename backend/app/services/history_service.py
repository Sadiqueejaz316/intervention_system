from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import HistoryAction
from app.models.ticket_history import TicketHistory


def record(
    db: Session,
    *,
    ticket_id: UUID,
    action: HistoryAction,
    user_id: UUID | None = None,
    old_status: str | None = None,
    new_status: str | None = None,
    comment: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> TicketHistory:
    """Add a history row to the caller's transaction. The caller commits."""
    entry = TicketHistory(
        ticket_id=ticket_id,
        user_id=user_id,
        action=action.value,
        old_status=old_status,
        new_status=new_status,
        comment=comment,
        meta=metadata or {},
    )
    db.add(entry)

    return entry


def list_for_ticket(db: Session, ticket_id: UUID) -> list[TicketHistory]:
    query = (
        select(TicketHistory)
        .where(TicketHistory.ticket_id == ticket_id)
        .order_by(TicketHistory.created_at)
    )

    return list(db.execute(query).scalars().all())
