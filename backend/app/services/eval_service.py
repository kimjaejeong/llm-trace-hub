from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Evaluation, Span, Trace
from app.schemas.eval import EvalCreateRequest


class EvalService:
    def __init__(self, db: Session, project_id):
        self.db = db
        self.project_id = project_id

    def create_eval(self, payload: EvalCreateRequest) -> Evaluation:
        if payload.trace_id:
            trace = self.db.scalar(
                select(Trace).where(and_(Trace.id == payload.trace_id, Trace.project_id == self.project_id))
            )
            if not trace:
                raise HTTPException(status_code=404, detail="trace not found")
        if payload.span_id:
            span = self.db.scalar(
                select(Span).where(and_(Span.id == payload.span_id, Span.project_id == self.project_id))
            )
            if not span:
                raise HTTPException(status_code=404, detail="span not found")

        eval_row = self.db.scalar(
            select(Evaluation).where(
                and_(Evaluation.project_id == self.project_id, Evaluation.idempotency_key == payload.idempotency_key)
            )
        )
        if eval_row:
            return eval_row

        eval_row = Evaluation(
            project_id=self.project_id,
            trace_id=payload.trace_id,
            span_id=payload.span_id,
            eval_name=payload.eval_name,
            eval_model=payload.eval_model,
            score=payload.score,
            passed=payload.passed,
            eval_metadata=payload.metadata,
            user_review_passed=payload.user_review_passed,
            idempotency_key=payload.idempotency_key,
        )
        self.db.add(eval_row)

        if payload.trace_id and payload.user_review_passed is not None:
            trace = self.db.get(Trace, payload.trace_id)
            if trace:
                trace.user_review_passed = payload.user_review_passed

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="idempotency conflict")
        self.db.refresh(eval_row)
        return eval_row
