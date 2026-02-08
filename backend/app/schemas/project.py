from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProjectCreateIn(BaseModel):
    name: str


class ProjectListItem(BaseModel):
    id: UUID
    name: str
    is_active: bool
    created_at: datetime
    trace_count: int
    open_case_count: int


class ProjectCreateOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    api_key: str
