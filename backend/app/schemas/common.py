from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StatusEnum(str, Enum):
    running = "running"
    success = "success"
    error = "error"


class ActionEnum(str, Enum):
    ALLOW_ANSWER = "ALLOW_ANSWER"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"
    ALLOW_WITH_WARNING = "ALLOW_WITH_WARNING"
    NEED_CLARIFICATION = "NEED_CLARIFICATION"


class BaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IdempotentIn(BaseModel):
    idempotency_key: str = Field(..., min_length=3, max_length=255)


JsonDict = dict[str, Any]
Timestamp = datetime
ID = UUID
