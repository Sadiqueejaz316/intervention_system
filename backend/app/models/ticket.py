import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, String, Text, case, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.core.enums import PRIORITY_RANK, TicketPriority, TicketStatus

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.ticket_history import TicketHistory
    from app.models.user import User


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Free-form string rather than a DB enum: issue types come from the adapter.
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    priority: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=TicketPriority.MEDIUM,
        server_default=TicketPriority.MEDIUM.value,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=TicketStatus.OPEN,
        server_default=TicketStatus.OPEN.value,
        index=True,
    )

    reporter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    location_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Mapped as `meta` because `metadata` is reserved by SQLAlchemy's declarative
    # base; the underlying column and the API field are both named "metadata".
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    reporter: Mapped["User | None"] = relationship("User", lazy="selectin")

    history: Mapped[list["TicketHistory"]] = relationship(
        "TicketHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Ticket {self.id} {self.status} {self.priority}>"


#: Queue ordering shared by every ticket listing: CRITICAL first, LOW last.
PRIORITY_ORDER = case(PRIORITY_RANK, value=Ticket.priority, else_=99)
