from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.judge.registry import JudgeRegistry
from app.models import Evaluation, JudgeCache, JudgeRun, Span, SpanEvent, Trace, TraceDecision
from app.schemas.common import ActionEnum
from app.schemas.decision import DecideRequest
from app.services.case_service import CaseService
from app.services.policy_engine import PolicyEngine
from app.services.policy_service import PolicyService
from app.services.utils import stable_hash


class DecisionService:
    def __init__(self, db: Session, project_id: UUID):
        self.db = db
        self.project_id = project_id
        self.policy_service = PolicyService(db, project_id)
        self.case_service = CaseService(db, project_id)
        self.registry = JudgeRegistry()

    def _build_context(self, trace: Trace, request_payload: dict[str, Any] | None, response_payload: dict[str, Any] | None):
        eval_rows = self.db.scalars(
            select(Evaluation).where(and_(Evaluation.project_id == self.project_id, Evaluation.trace_id == trace.id))
        ).all()
        eval_map = {row.eval_name: {"score": row.score, "passed": row.passed, "eval_model": row.eval_model} for row in eval_rows}
        overall = sum((row.score for row in eval_rows), 0.0) / len(eval_rows) if eval_rows else 0.8

        context = {
            "trace": {
                "id": str(trace.id),
                "status": trace.status,
                "model": trace.model,
                "environment": trace.environment,
                "user_id": trace.user_id,
                "session_id": trace.session_id,
            },
            "request": request_payload or {},
            "response": response_payload or {},
            "input_text": trace.input_text,
            "output_text": trace.output_text,
            "evals": {
                **eval_map,
                "overall_score": overall,
                "faithfulness_score": eval_map.get("faithfulness", {}).get("score", 0.8),
            },
            "safety": (request_payload or {}).get("safety", {}),
        }
        return context

    async def decide(self, payload: DecideRequest) -> dict[str, Any]:
        existing = self.db.scalar(
            select(TraceDecision).where(
                and_(TraceDecision.project_id == self.project_id, TraceDecision.idempotency_key == payload.idempotency_key)
            )
        )
        if existing:
            return {
                "decision": existing,
                "judge_runs": self.db.scalars(
                    select(JudgeRun).where(and_(JudgeRun.project_id == self.project_id, JudgeRun.trace_id == existing.trace_id))
                ).all(),
            }

        if not payload.trace_id:
            raise HTTPException(status_code=400, detail="trace_id is required for MVP")

        trace = self.db.scalar(select(Trace).where(and_(Trace.id == payload.trace_id, Trace.project_id == self.project_id)))
        if not trace:
            raise HTTPException(status_code=404, detail="trace not found")

        active_policy = self.policy_service.get_active_version(payload.force_policy_id, payload.force_policy_version)
        if not active_policy:
            raise HTTPException(status_code=400, detail="no active policy")

        context = self._build_context(trace, payload.request_payload, payload.response_payload)
        input_hash = stable_hash(
            {
                "trace_id": str(trace.id),
                "input_text": trace.input_text,
                "output_text": trace.output_text,
                "request": payload.request_payload,
                "response": payload.response_payload,
                "evals": context["evals"],
            }
        )
        policy_ver_key = f"{active_policy.policy_id}:v{active_policy.version}"

        cached = self.db.scalar(
            select(JudgeCache).where(
                and_(
                    JudgeCache.project_id == self.project_id,
                    JudgeCache.input_hash == input_hash,
                    JudgeCache.policy_version == policy_ver_key,
                )
            )
        )
        judge_runs: list[JudgeRun] = []
        if cached:
            selected = cached.decision
        else:
            heuristic_provider = self.registry.get("heuristic")
            heuristic_out = await heuristic_provider.judge(context)
            heuristic_run = JudgeRun(
                project_id=self.project_id,
                trace_id=trace.id,
                provider="heuristic",
                model="rules-v1",
                action=heuristic_out["action"],
                reason_code=heuristic_out["reason_code"],
                confidence=heuristic_out["confidence"],
                output=heuristic_out,
            )
            self.db.add(heuristic_run)
            judge_runs.append(heuristic_run)

            selected = heuristic_out
            if not (
                heuristic_out["action"] in {ActionEnum.BLOCK.value, ActionEnum.ESCALATE.value}
                and heuristic_out["confidence"] >= 0.9
            ):
                llm_provider = self.registry.get("llm")
                llm_out = await llm_provider.judge(context)
                llm_run = JudgeRun(
                    project_id=self.project_id,
                    trace_id=trace.id,
                    provider="llm",
                    model="gpt-judge",
                    action=llm_out["action"],
                    reason_code=llm_out["reason_code"],
                    confidence=llm_out["confidence"],
                    output=llm_out,
                )
                self.db.add(llm_run)
                judge_runs.append(llm_run)
                selected = llm_out

            self.db.add(
                JudgeCache(
                    project_id=self.project_id,
                    input_hash=input_hash,
                    policy_version=policy_ver_key,
                    decision=selected,
                )
            )

        engine = PolicyEngine(active_policy.definition)
        policy_result = engine.evaluate(
            {
                "request": payload.request_payload or {},
                "response": payload.response_payload or {},
                "evals": context["evals"],
                "signals": selected.get("signals", {}),
                "safety": context["safety"],
            }
        )

        final_action = policy_result.action or selected["action"]
        reason_code = policy_result.reason_code or selected["reason_code"]
        severity = policy_result.severity

        judge_span_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        self.db.add(
            Span(
                id=judge_span_id,
                project_id=self.project_id,
                trace_id=trace.id,
                parent_span_id=None,
                name="Decision Judge",
                span_type="judge",
                status="success",
                start_time=now,
                end_time=now,
                error=None,
                attributes={"policy_version": policy_ver_key},
                idempotency_key=f"judge-span:{payload.idempotency_key}",
            )
        )
        self.db.add(
            SpanEvent(
                project_id=self.project_id,
                trace_id=trace.id,
                span_id=judge_span_id,
                event_type="EVENT",
                event_time=now,
                payload={"judge_output": selected, "policy_result": policy_result.__dict__},
                idempotency_key=f"judge-event:{payload.idempotency_key}",
            )
        )

        decision = TraceDecision(
            project_id=self.project_id,
            trace_id=trace.id,
            action=final_action,
            reason_code=reason_code,
            severity=severity,
            confidence=float(selected.get("confidence", 0.5)),
            policy_version=policy_ver_key,
            judge_model="gpt-judge" if any(r.provider == "llm" for r in judge_runs) else "heuristic",
            signals=selected.get("signals", {}),
            rationale=selected.get("rationale"),
            idempotency_key=payload.idempotency_key,
        )
        self.db.add(decision)

        trace.decision = {
            "action": decision.action,
            "reason_code": decision.reason_code,
            "severity": decision.severity,
            "confidence": decision.confidence,
            "policy_version": decision.policy_version,
            "judge_model": decision.judge_model,
        }

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="idempotency conflict")

        self.db.refresh(decision)

        if decision.action == ActionEnum.ESCALATE.value:
            await self.case_service.create_case_and_notify(trace.id, decision.reason_code)

        recent_judge_runs = self.db.scalars(
            select(JudgeRun)
            .where(and_(JudgeRun.project_id == self.project_id, JudgeRun.trace_id == trace.id))
            .order_by(JudgeRun.created_at.desc())
            .limit(5)
        ).all()
        return {"decision": decision, "judge_runs": recent_judge_runs}
