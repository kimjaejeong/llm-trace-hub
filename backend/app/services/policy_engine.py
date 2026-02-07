from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.common import ActionEnum
from app.services.utils import get_nested


@dataclass
class EvaluatedRule:
    matched: bool
    action: str | None = None
    reason_code: str | None = None
    severity: str = "medium"


class PolicyEngine:
    def __init__(self, definition: dict[str, Any]):
        self.definition = definition
        self.rules = sorted(definition.get("rules", []), key=lambda x: x.get("priority", 9999))

    @staticmethod
    def _compare(op: str, actual: Any, expected: Any) -> bool:
        if op == "eq":
            return actual == expected
        if op == "ne":
            return actual != expected
        if op == "lt":
            return actual is not None and actual < expected
        if op == "lte":
            return actual is not None and actual <= expected
        if op == "gt":
            return actual is not None and actual > expected
        if op == "gte":
            return actual is not None and actual >= expected
        if op == "contains" and isinstance(actual, str):
            return str(expected).lower() in actual.lower()
        if op == "in":
            return actual in expected
        return False

    def _condition_match(self, condition: dict[str, Any], context: dict[str, Any]) -> bool:
        field = condition.get("field")
        op = condition.get("op", "eq")
        expected = condition.get("value")
        actual = get_nested(context, field) if field else None
        return self._compare(op, actual, expected)

    def evaluate(self, context: dict[str, Any]) -> EvaluatedRule:
        for rule in self.rules:
            when = rule.get("when", {})
            all_conditions = when.get("all", [])
            any_conditions = when.get("any", [])

            all_ok = all(self._condition_match(c, context) for c in all_conditions) if all_conditions else True
            any_ok = any(self._condition_match(c, context) for c in any_conditions) if any_conditions else True

            if all_ok and any_ok:
                then = rule.get("then", {})
                action = then.get("action", ActionEnum.ALLOW_ANSWER.value)
                return EvaluatedRule(
                    matched=True,
                    action=action,
                    reason_code=then.get("reason_code", "POLICY_MATCH"),
                    severity=then.get("severity", "medium"),
                )

        return EvaluatedRule(matched=False, action=ActionEnum.ALLOW_ANSWER.value, reason_code="DEFAULT_ALLOW", severity="low")
