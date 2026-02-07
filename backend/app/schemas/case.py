from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CaseOut(BaseModel):
    id: UUID
    trace_id: UUID
    reason_code: str
    status: str
    assignee: str | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime


class CaseActionRequest(BaseModel):
    assignee: str | None = None
