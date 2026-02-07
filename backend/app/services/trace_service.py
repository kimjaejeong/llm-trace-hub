from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Text, and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Evaluation, JudgeRun, Span, SpanEvent, Trace, TraceDecision
from app.schemas.ingest import IngestSpansRequest, IngestTraceBatchRequest, SpanEventType
class TraceService:
    def __init__(self, db: Session, project_id: UUID):
        self.db = db
        self.project_id = project_id

    def _recalculate_trace_metrics(self, trace_id: UUID) -> None:
        counts = self.db.execute(
            select(
                func.count(Span.id).label("total"),
                func.count(Span.id).filter(Span.end_time.is_not(None)).label("ended"),
            ).where(and_(Span.project_id == self.project_id, Span.trace_id == trace_id))
        ).one()

        trace = self.db.get(Trace, trace_id)
        if not trace:
            return

        total = int(counts.total or 0)
        ended = int(counts.ended or 0)
        trace.total_spans = total
        trace.ended_spans = ended
        trace.has_open_spans = total > ended
        trace.completion_rate = float(ended / total) if total else 1.0
        if trace.end_time and not trace.has_open_spans:
            trace.status = "success" if trace.status == "running" else trace.status

    def ingest_trace_batch(self, payload: IngestTraceBatchRequest) -> dict[str, Any]:
        trace_data = payload.trace
        trace = self.db.get(Trace, trace_data.trace_id)

        if not trace:
            trace = Trace(
                id=trace_data.trace_id,
                project_id=self.project_id,
                external_trace_id=trace_data.external_trace_id,
                status=trace_data.status,
                start_time=trace_data.start_time,
                end_time=trace_data.end_time,
                attributes=trace_data.attributes,
                model=trace_data.model,
                environment=trace_data.environment,
                user_id=trace_data.user_id,
                session_id=trace_data.session_id,
                input_text=trace_data.input_text,
                output_text=trace_data.output_text,
                user_review_passed=trace_data.user_review_passed,
            )
            self.db.add(trace)
        else:
            # materialized snapshot update; immutable event history remains in span_events
            trace.status = trace_data.status
            trace.end_time = trace_data.end_time
            trace.attributes = {**(trace.attributes or {}), **trace_data.attributes}
            trace.model = trace_data.model or trace.model
            trace.environment = trace_data.environment or trace.environment
            trace.user_id = trace_data.user_id or trace.user_id
            trace.session_id = trace_data.session_id or trace.session_id
            trace.input_text = trace_data.input_text or trace.input_text
            trace.output_text = trace_data.output_text or trace.output_text
            if trace_data.user_review_passed is not None:
                trace.user_review_passed = trace_data.user_review_passed

        batch_span_ids = {s.span_id for s in payload.spans}
        for span_data in payload.spans:
            if span_data.parent_span_id and span_data.parent_span_id not in batch_span_ids and not payload.allow_missing_parent:
                parent = self.db.get(Span, span_data.parent_span_id)
                if not parent:
                    raise HTTPException(status_code=400, detail=f"parent span not found: {span_data.parent_span_id}")

            span = self.db.scalar(
                select(Span).where(
                    and_(Span.project_id == self.project_id, Span.idempotency_key == span_data.idempotency_key)
                )
            )
            if span:
                continue

            self.db.add(
                Span(
                    id=span_data.span_id,
                    project_id=self.project_id,
                    trace_id=span_data.trace_id,
                    parent_span_id=span_data.parent_span_id,
                    name=span_data.name,
                    span_type=span_data.span_type,
                    status=span_data.status,
                    start_time=span_data.start_time,
                    end_time=span_data.end_time,
                    error=span_data.error,
                    attributes=span_data.attributes,
                    idempotency_key=span_data.idempotency_key,
                )
            )
            self.db.add(
                SpanEvent(
                    project_id=self.project_id,
                    trace_id=span_data.trace_id,
                    span_id=span_data.span_id,
                    event_type=SpanEventType.SPAN_STARTED.value,
                    event_time=span_data.start_time,
                    payload={"name": span_data.name, "attributes": span_data.attributes},
                    idempotency_key=f"{span_data.idempotency_key}:start",
                )
            )
            if span_data.end_time:
                self.db.add(
                    SpanEvent(
                        project_id=self.project_id,
                        trace_id=span_data.trace_id,
                        span_id=span_data.span_id,
                        event_type=SpanEventType.SPAN_ENDED.value,
                        event_time=span_data.end_time,
                        payload={"status": span_data.status, "error": span_data.error},
                        idempotency_key=f"{span_data.idempotency_key}:end",
                    )
                )

        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="idempotency conflict")

        self._recalculate_trace_metrics(trace_data.trace_id)
        self.db.commit()
        return {"trace_id": str(trace_data.trace_id), "ingested_spans": len(payload.spans)}

    def ingest_span_events(self, payload: IngestSpansRequest) -> dict[str, Any]:
        ingested = 0
        for event in payload.events:
            duplicate = self.db.scalar(
                select(SpanEvent.id).where(
                    and_(SpanEvent.project_id == self.project_id, SpanEvent.idempotency_key == event.idempotency_key)
                )
            )
            if duplicate:
                continue

            if event.span_id and event.event_type == SpanEventType.SPAN_STARTED:
                span = self.db.get(Span, event.span_id)
                if not span:
                    span_payload = event.payload
                    parent_span_id = span_payload.get("parent_span_id")
                    if parent_span_id and not payload.allow_missing_parent:
                        parent = self.db.get(Span, parent_span_id)
                        if not parent:
                            raise HTTPException(status_code=400, detail=f"parent span not found: {parent_span_id}")

                    self.db.add(
                        Span(
                            id=event.span_id,
                            project_id=self.project_id,
                            trace_id=event.trace_id,
                            parent_span_id=parent_span_id,
                            name=span_payload.get("name", "span"),
                            span_type=span_payload.get("span_type", "task"),
                            status=span_payload.get("status", "running"),
                            start_time=event.event_time,
                            attributes=span_payload.get("attributes", {}),
                            idempotency_key=span_payload.get("idempotency_key", event.idempotency_key),
                        )
                    )

            if event.span_id and event.event_type == SpanEventType.SPAN_ENDED:
                span = self.db.get(Span, event.span_id)
                if span:
                    span.end_time = event.event_time
                    span.status = event.payload.get("status", span.status)
                    span.error = event.payload.get("error", span.error)

            if event.span_id and event.event_type == SpanEventType.AMENDMENT:
                span = self.db.get(Span, event.span_id)
                if span:
                    patch = event.payload.get("patch", {})
                    # projection update while preserving immutable amendment event log
                    span.attributes = {**(span.attributes or {}), **patch.get("attributes", {})}
                    if "status" in patch:
                        span.status = patch["status"]

            self.db.add(
                SpanEvent(
                    project_id=self.project_id,
                    trace_id=event.trace_id,
                    span_id=event.span_id,
                    event_type=event.event_type.value,
                    event_time=event.event_time,
                    payload=event.payload,
                    idempotency_key=event.idempotency_key,
                )
            )
            ingested += 1

        touched_trace_ids = {e.trace_id for e in payload.events}
        for trace_id in touched_trace_ids:
            self._recalculate_trace_metrics(trace_id)

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="idempotency conflict")

        return {"ingested_events": ingested}

    def list_traces(
        self,
        page: int,
        page_size: int,
        start_time: datetime | None,
        end_time: datetime | None,
        status: str | None,
        tag: str | None,
        model: str | None,
        environment: str | None,
        user_id: str | None,
        session_id: str | None,
        search: str | None,
    ) -> dict[str, Any]:
        q = select(Trace).where(Trace.project_id == self.project_id)

        if start_time:
            q = q.where(Trace.start_time >= start_time)
        if end_time:
            q = q.where(Trace.start_time <= end_time)
        if status:
            q = q.where(Trace.status == status)
        if model:
            q = q.where(Trace.model == model)
        if environment:
            q = q.where(Trace.environment == environment)
        if user_id:
            q = q.where(Trace.user_id == user_id)
        if session_id:
            q = q.where(Trace.session_id == session_id)
        if tag:
            q = q.where(Trace.attributes.op("?")(tag))
        if search:
            q = q.where(
                or_(
                    Trace.input_text.ilike(f"%{search}%"),
                    Trace.output_text.ilike(f"%{search}%"),
                    Trace.id.in_(
                        select(SpanEvent.trace_id).where(
                            and_(
                                SpanEvent.project_id == self.project_id,
                                func.cast(SpanEvent.payload, Text).ilike(f"%{search}%"),
                            )
                        )
                    ),
                )
            )

        total = self.db.scalar(select(func.count()).select_from(q.subquery())) or 0
        rows = self.db.scalars(
            q.order_by(Trace.start_time.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return {
            "items": rows,
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def get_trace_detail(self, trace_id: UUID) -> dict[str, Any]:
        trace = self.db.scalar(select(Trace).where(and_(Trace.id == trace_id, Trace.project_id == self.project_id)))
        if not trace:
            raise HTTPException(status_code=404, detail="trace not found")

        spans = self.db.scalars(
            select(Span).where(and_(Span.trace_id == trace_id, Span.project_id == self.project_id)).order_by(Span.start_time.asc())
        ).all()
        events = self.db.scalars(
            select(SpanEvent)
            .where(and_(SpanEvent.trace_id == trace_id, SpanEvent.project_id == self.project_id))
            .order_by(SpanEvent.event_time.asc())
        ).all()
        evals = self.db.scalars(
            select(Evaluation)
            .where(and_(Evaluation.project_id == self.project_id, Evaluation.trace_id == trace_id))
            .order_by(Evaluation.created_at.desc())
        ).all()
        decisions = self.db.scalars(
            select(TraceDecision)
            .where(and_(TraceDecision.project_id == self.project_id, TraceDecision.trace_id == trace_id))
            .order_by(TraceDecision.created_at.desc())
        ).all()
        judge_runs = self.db.scalars(
            select(JudgeRun)
            .where(and_(JudgeRun.project_id == self.project_id, JudgeRun.trace_id == trace_id))
            .order_by(JudgeRun.created_at.desc())
        ).all()

        timeline = []
        timeline.append(
            {
                "timestamp": trace.start_time,
                "source": "trace",
                "source_id": trace.id,
                "event_type": "TRACE_STARTED",
                "payload": {"status": trace.status},
            }
        )
        for event in events:
            timeline.append(
                {
                    "timestamp": event.event_time,
                    "source": "span",
                    "source_id": event.span_id,
                    "event_type": event.event_type,
                    "payload": event.payload,
                }
            )
        if trace.end_time:
            timeline.append(
                {
                    "timestamp": trace.end_time,
                    "source": "trace",
                    "source_id": trace.id,
                    "event_type": "TRACE_ENDED",
                    "payload": {"status": trace.status},
                }
            )

        timeline.sort(key=lambda x: x["timestamp"])
        return {
            "trace": trace,
            "spans": spans,
            "timeline": timeline,
            "evaluations": [
                {
                    "id": e.id,
                    "trace_id": e.trace_id,
                    "span_id": e.span_id,
                    "eval_name": e.eval_name,
                    "eval_model": e.eval_model,
                    "score": e.score,
                    "passed": e.passed,
                    "metadata": e.eval_metadata or {},
                    "user_review_passed": e.user_review_passed,
                    "created_at": e.created_at,
                }
                for e in evals
            ],
            "decision_history": decisions,
            "judge_runs": judge_runs,
        }
