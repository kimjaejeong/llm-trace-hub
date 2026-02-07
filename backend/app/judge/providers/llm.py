from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.judge.providers.base import JudgeProvider


class LLMJudgeOutput(BaseModel):
    action: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason_code: str
    rationale: str
    signals: dict[str, float | bool]


class LLMJudgeProvider(JudgeProvider):
    name = "llm"

    def __init__(self, endpoint: str | None = None, model: str = "gpt-judge"):
        self.endpoint = endpoint
        self.model = model

    async def judge(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.endpoint:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.endpoint, json={"model": self.model, "payload": payload})
                response.raise_for_status()
                data = response.json()
                return LLMJudgeOutput.model_validate(data).model_dump()

        # Fallback stub output for local MVP.
        score = payload.get("evals", {}).get("overall_score", 0.8)
        action = "ALLOW_ANSWER" if score >= 0.5 else "NEED_CLARIFICATION"
        data = {
            "action": action,
            "confidence": 0.65,
            "reason_code": "LLM_JUDGE_STUB",
            "rationale": "stubbed llm judge",
            "signals": {
                "pii": False,
                "hallucination_risk": max(0.0, 1.0 - float(score)),
                "financial_risk": 0.2,
            },
        }
        return LLMJudgeOutput.model_validate(data).model_dump()
