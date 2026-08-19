from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssignmentCreate(BaseModel):
    contractor_id: UUID
    notes: str | None = Field(default=None, max_length=2000)


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: UUID
    contractor_id: UUID
    assigned_by: UUID | None
    assigned_at: datetime
    accepted_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    notes: str | None


class WorkerRecommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    worker_id: UUID
    name: str
    score: int
    reasons: list[str]
