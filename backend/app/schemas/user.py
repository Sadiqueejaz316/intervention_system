from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import UserRole


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    role: UserRole
    skills: list[str] = Field(default_factory=list)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_available: bool = True


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    # Plain str on the way out: addresses are validated on write, and re-validating
    # stored data here would turn one odd row into a 500 for the whole listing.
    email: str
    role: UserRole
    skills: list[str]
    latitude: float | None
    longitude: float | None
    is_available: bool
    created_at: datetime
    updated_at: datetime


class WorkerRead(UserRead):
    active_ticket_count: int = 0

    @classmethod
    def from_user(cls, user: Any, active_ticket_count: int) -> "WorkerRead":
        return cls(
            **UserRead.model_validate(user).model_dump(),
            active_ticket_count=active_ticket_count,
        )


class WorkerSummary(BaseModel):
    """Just enough about a worker to label a ticket in a queue or on a card."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    skills: list[str] = Field(default_factory=list)
    is_available: bool
