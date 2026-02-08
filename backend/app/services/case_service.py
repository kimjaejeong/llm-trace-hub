from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import and_, func, select
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

    def list_cases(
        self,
        status: str | None,
        assignee: str | None,
        reason_code: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        q = select(Case).where(Case.project_id == self.project_id)
        if status:
            q = q.where(Case.status == status)
        if assignee:
            q = q.where(Case.assignee == assignee)
        if reason_code:
            q = q.where(Case.reason_code == reason_code)

        total = self.db.scalar(select(func.count()).select_from(q.subquery())) or 0
        rows = self.db.scalars(
            q.order_by(Case.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return {
            "items": rows,
            "page": page,
            "page_size": page_size,
            "total": total,
            "stats": self.case_stats(),
        }

    def case_stats(self) -> dict:
        status_rows = self.db.execute(
            select(Case.status, func.count(Case.id)).where(Case.project_id == self.project_id).group_by(Case.status)
        ).all()
        overdue_at = datetime.now(timezone.utc) - timedelta(hours=24)
        overdue_open = self.db.scalar(
            select(func.count(Case.id)).where(
                and_(
                    Case.project_id == self.project_id,
                    Case.status == "open",
                    Case.created_at < overdue_at,
                )
            )
        ) or 0
        return {
            "by_status": {k: int(v) for k, v in status_rows},
            "overdue_open_24h": int(overdue_open),
        }

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
