from __future__ import annotations

import hashlib
import secrets
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import Case, Project, Trace


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def list_projects(self) -> list[dict]:
        projects = self.db.scalars(select(Project).order_by(Project.created_at.desc())).all()
        items: list[dict] = []
        for project in projects:
            trace_count = self.db.scalar(
                select(func.count(Trace.id)).where(Trace.project_id == project.id)
            ) or 0
            open_case_count = self.db.scalar(
                select(func.count(Case.id)).where(
                    and_(Case.project_id == project.id, Case.status.in_(["open", "acknowledged"]))
                )
            ) or 0
            items.append(
                {
                    "id": project.id,
                    "name": project.name,
                    "is_active": bool(project.is_active),
                    "created_at": project.created_at,
                    "trace_count": int(trace_count),
                    "open_case_count": int(open_case_count),
                }
            )
        return items

    def create_project(self, name: str) -> dict:
        api_key = f"proj_{secrets.token_urlsafe(18)}"
        key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        project = Project(name=name, api_key_hash=key_hash)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return {
            "id": project.id,
            "name": project.name,
            "created_at": project.created_at,
            "api_key": api_key,
        }

    def _get_project(self, project_id: UUID) -> Project:
        project = self.db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project not found")
        return project

    def rotate_project_key(self, project_id: UUID) -> dict:
        project = self._get_project(project_id)
        api_key = f"proj_{secrets.token_urlsafe(18)}"
        project.api_key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        self.db.commit()
        self.db.refresh(project)
        return {
            "id": project.id,
            "name": project.name,
            "created_at": project.created_at,
            "api_key": api_key,
        }

    def set_project_active(self, project_id: UUID, is_active: bool) -> dict:
        project = self._get_project(project_id)
        project.is_active = is_active
        self.db.commit()
        self.db.refresh(project)
        return {
            "id": project.id,
            "name": project.name,
            "is_active": bool(project.is_active),
            "created_at": project.created_at,
        }
