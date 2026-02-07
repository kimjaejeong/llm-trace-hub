from typing import Any

from app.judge.providers.base import JudgeProvider
from app.schemas.common import ActionEnum


class HeuristicJudgeProvider(JudgeProvider):
    name = "heuristic"

    async def judge(self, payload: dict[str, Any]) -> dict[str, Any]:
        input_text = str(payload.get("input_text") or "")
        output_text = str(payload.get("output_text") or "")
        evals = payload.get("evals", {})

        pii_signal = any(token in input_text.lower() for token in ["ssn", "credit card", "passport"])
        financial_risk = 0.9 if "investment advice" in output_text.lower() else 0.1
        hallucination_risk = 1.0 - float(evals.get("faithfulness_score", 0.8))

        if pii_signal:
            action = ActionEnum.ESCALATE.value
            reason = "PII_DETECTED"
        elif financial_risk > 0.85:
            action = ActionEnum.ALLOW_WITH_WARNING.value
            reason = "FINANCIAL_RISK"
        elif hallucination_risk > 0.8:
            action = ActionEnum.NEED_CLARIFICATION.value
            reason = "HALLUCINATION_RISK"
        else:
            action = ActionEnum.ALLOW_ANSWER.value
            reason = "HEURISTIC_OK"

        confidence = 0.95 if action in {ActionEnum.ESCALATE.value, ActionEnum.BLOCK.value} else 0.7
        return {
            "action": action,
            "confidence": confidence,
            "reason_code": reason,
            "rationale": "heuristic pre-check",
            "signals": {
                "pii": pii_signal,
                "hallucination_risk": hallucination_risk,
                "financial_risk": financial_risk,
            },
        }
