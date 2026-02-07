from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Case, Notification


class CaseService:
    def __init__(self, db: Session, project_id: UUID):
        self.db = db
        self.project_id = project_id

    async def create_case_and_notify(self, trace_id: UUID, reason_code: str) -> Case:
        case = Case(project_id=self.project_id, trace_id=trace_id, reason_code=reason_code, status="open")
        self.db.add(case)
        self.db.flush()

        if settings.webhook_url:
            payload = {
                "case_id": str(case.id),
                "trace_id": str(trace_id),
                "reason_code": reason_code,
                "status": case.status,
                "created_at": case.created_at.isoformat(),
            }
            notification = Notification(
                project_id=self.project_id,
                case_id=case.id,
                channel="webhook",
                target_url=settings.webhook_url,
                status="pending",
                payload=payload,
            )
            self.db.add(notification)
            self.db.flush()

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(settings.webhook_url, json=payload)
                    notification.status = "sent" if response.status_code < 300 else "failed"
                    notification.response_snippet = response.text[:500]
            except Exception as exc:
                notification.status = "failed"
                notification.response_snippet = str(exc)[:500]

        self.db.commit()
        self.db.refresh(case)
        return case

    def list_cases(self, status: str | None) -> list[Case]:
        q = select(Case).where(Case.project_id == self.project_id)
        if status:
            q = q.where(Case.status == status)
        return self.db.scalars(q.order_by(Case.created_at.desc())).all()

    def get_case(self, case_id: UUID) -> Case:
        case = self.db.scalar(select(Case).where(and_(Case.id == case_id, Case.project_id == self.project_id)))
        if not case:
            raise HTTPException(status_code=404, detail="case not found")
        return case

    def ack_case(self, case_id: UUID, assignee: str | None) -> Case:
        case = self.get_case(case_id)
        case.status = "acknowledged"
        case.assignee = assignee or case.assignee
        case.acknowledged_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(case)
        return case

    def resolve_case(self, case_id: UUID, assignee: str | None) -> Case:
        case = self.get_case(case_id)
        case.status = "resolved"
        case.assignee = assignee or case.assignee
        if not case.acknowledged_at:
            case.acknowledged_at = datetime.now(timezone.utc)
        case.resolved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(case)
        return case
