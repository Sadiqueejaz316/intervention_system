import uuid

from sqlalchemy import Boolean, Float, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Nullable so seeded or imported accounts can exist before a password is set;
    # such an account simply cannot log in. Never leaves the API.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # JSONB: the skill vocabulary is defined by the active domain adapter,
    # so it must not be frozen into the schema.
    skills: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
