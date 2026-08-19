from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.core.enums import TicketPriority, TicketStatus
from app.schemas.user import WorkerSummary


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str | None = None
    # Validated against the active domain adapter, not against an enum.
    type: str = Field(min_length=1, max_length=100)
    priority: TicketPriority = TicketPriority.MEDIUM
    location_text: str | None = Field(default=None, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    comment: str | None = Field(default=None, max_length=2000)


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    title: str
    description: str | None
    type: str
    priority: TicketPriority
    status: TicketStatus
    reporter_id: UUID | None
    location_text: str | None
    latitude: float | None
    longitude: float | None
    # Reads the ORM attribute `meta` but is exposed as "metadata" over the API.
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("meta", "metadata"),
    )
    created_at: datetime
    updated_at: datetime
    #: Worker holding the current assignment, if any.
    assigned_worker: WorkerSummary | None = None

    @classmethod
    def from_ticket(cls, ticket: Any, worker: Any | None = None) -> "TicketRead":
        read = cls.model_validate(ticket)
        if worker is not None:
            read.assigned_worker = WorkerSummary.model_validate(worker)

        return read


class TicketHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    ticket_id: UUID
    user_id: UUID | None
    action: str
    old_status: str | None
    new_status: str | None
    comment: str | None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("meta", "metadata"),
    )
    created_at: datetime
