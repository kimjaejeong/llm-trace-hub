from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import JsonDict


class PolicyRuleWhen(BaseModel):
    all: list[JsonDict] | None = None
    any: list[JsonDict] | None = None


class PolicyRuleThen(BaseModel):
    action: str
    reason_code: str
    severity: str = "medium"


class PolicyRule(BaseModel):
    priority: int
    when: PolicyRuleWhen
    then: PolicyRuleThen
    metadata: JsonDict = Field(default_factory=dict)


class PolicyCreateRequest(BaseModel):
    name: str
    description: str | None = None
    effective_from: datetime
    active: bool = False
    definition: JsonDict


class PolicyOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime


class PolicyVersionOut(BaseModel):
    id: UUID
    policy_id: UUID
    version: int
    effective_from: datetime
    active: bool
    definition: JsonDict
    created_at: datetime
