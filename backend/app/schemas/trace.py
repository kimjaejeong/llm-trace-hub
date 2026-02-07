from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import JsonDict
from app.schemas.decision import DecisionOut, JudgeRunOut
from app.schemas.eval import EvalOut


class TraceListItem(BaseModel):
    id: UUID
    status: str
    start_time: datetime
    end_time: datetime | None
    model: str | None
    environment: str | None
    user_id: str | None
    session_id: str | None
    completion_rate: float
    has_open_spans: bool
    user_review_passed: bool | None
    decision: JsonDict | None = None


class SpanNode(BaseModel):
    id: UUID
    parent_span_id: UUID | None
    name: str
    span_type: str
    status: str
    start_time: datetime
    end_time: datetime | None
    error: str | None
    attributes: JsonDict


class TimelineItem(BaseModel):
    timestamp: datetime
    source: str
    source_id: UUID | None
    event_type: str
    payload: JsonDict = Field(default_factory=dict)


class TraceDetail(BaseModel):
    trace: TraceListItem
    spans: list[SpanNode]
    timeline: list[TimelineItem]
    evaluations: list[EvalOut]
    decision_history: list[DecisionOut]
    judge_runs: list[JudgeRunOut]
