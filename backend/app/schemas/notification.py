from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import NotificationType


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    ticket_id: UUID | None
    title: str
    message: str
    type: NotificationType
    is_read: bool
    created_at: datetime
