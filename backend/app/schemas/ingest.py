from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import JsonDict


class SpanUpsert(BaseModel):
    span_id: UUID
    trace_id: UUID
    parent_span_id: UUID | None = None
    name: str
    span_type: str = "task"
    status: str = "running"
    start_time: datetime
    end_time: datetime | None = None
    error: str | None = None
    attributes: JsonDict = Field(default_factory=dict)
    idempotency_key: str


class TraceUpsert(BaseModel):
    trace_id: UUID
    external_trace_id: str | None = None
    status: str = "running"
    start_time: datetime
    end_time: datetime | None = None
    attributes: JsonDict = Field(default_factory=dict)
    model: str | None = None
    environment: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    input_text: str | None = None
    output_text: str | None = None
    user_review_passed: bool | None = None


class IngestTraceBatchRequest(BaseModel):
    trace: TraceUpsert
    spans: list[SpanUpsert] = Field(default_factory=list)
    allow_missing_parent: bool = True


class SpanEventType(str, Enum):
    SPAN_STARTED = "SPAN_STARTED"
    SPAN_ENDED = "SPAN_ENDED"
    LOG = "LOG"
    EVENT = "EVENT"
    AMENDMENT = "AMENDMENT"


class SpanEventIn(BaseModel):
    trace_id: UUID
    span_id: UUID | None = None
    event_type: SpanEventType
    event_time: datetime
    payload: JsonDict = Field(default_factory=dict)
    idempotency_key: str

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, value: JsonDict) -> JsonDict:
        if not isinstance(value, dict):
            raise ValueError("payload must be object")
        return value


class IngestSpansRequest(BaseModel):
    events: list[SpanEventIn]
    allow_missing_parent: bool = True
