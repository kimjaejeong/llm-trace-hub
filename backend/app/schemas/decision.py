from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ActionEnum, JsonDict


class DecideRequest(BaseModel):
    trace_id: UUID | None = None
    request_payload: JsonDict | None = None
    response_payload: JsonDict | None = None
    force_policy_id: UUID | None = None
    force_policy_version: int | None = None
    idempotency_key: str


class DecisionOut(BaseModel):
    action: ActionEnum
    reason_code: str
    severity: str
    confidence: float
    policy_version: str
    judge_model: str | None = None
    rationale: str | None = None
    signals: JsonDict = Field(default_factory=dict)


class JudgeRunOut(BaseModel):
    provider: str
    model: str | None
    action: str
    reason_code: str
    confidence: float
    output: JsonDict
    created_at: datetime
