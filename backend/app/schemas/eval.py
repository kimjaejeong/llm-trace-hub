from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import JsonDict


class EvalCreateRequest(BaseModel):
    trace_id: UUID | None = None
    span_id: UUID | None = None
    eval_name: str
    eval_model: str
    score: float
    passed: bool
    metadata: JsonDict = Field(default_factory=dict)
    user_review_passed: bool | None = None
    idempotency_key: str

    @model_validator(mode="after")
    def check_target(self):
        if not self.trace_id and not self.span_id:
            raise ValueError("trace_id or span_id is required")
        return self


class EvalOut(BaseModel):
    id: UUID
    trace_id: UUID | None
    span_id: UUID | None
    eval_name: str
    eval_model: str
    score: float
    passed: bool
    metadata: JsonDict
    user_review_passed: bool | None
    created_at: datetime
