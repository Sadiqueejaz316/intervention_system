import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class TicketHistory(Base):
    __tablename__ = "ticket_history"
    __table_args__ = (
        Index("ix_ticket_history_ticket_id_created_at", "ticket_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Nullable so system-generated events can be recorded without an actor.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(String(50), nullable=False)

    old_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    # Set in Python because Postgres' now() is constant within a transaction,
    # and several entries can be written in one transaction; the timeline needs
    # them in insertion order.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="history")

    def __repr__(self) -> str:
        return f"<TicketHistory {self.action} on {self.ticket_id}>"
