from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProjectCreateIn(BaseModel):
    name: str


class ProjectListItem(BaseModel):
    id: UUID
    name: str
    is_active: bool
    key_activated: bool
    created_at: datetime
    trace_count: int
    open_case_count: int


class ProjectCreateOut(BaseModel):
    id: UUID
    name: str
    key_activated: bool
    created_at: datetime
    api_key: str


class ProjectCurrentKeyOut(BaseModel):
    project_id: UUID
    key_activated: bool
    api_key: str | None
