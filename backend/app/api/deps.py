import hashlib
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import Project


def _is_admin_key(x_api_key: str) -> bool:
    if x_api_key == settings.internal_api_key_seed:
        return True
    if settings.environment == "dev" and x_api_key == "dev-key":
        return True
    return False


async def get_project(
    x_api_key: str | None = Header(default=None),
    x_project_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Project:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    if x_project_id and _is_admin_key(x_api_key):
        try:
            project_id = UUID(x_project_id)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid x-project-id") from exc
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if not project.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project is inactive")
        return project

    key_hash = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    project = db.scalar(select(Project).where(Project.api_key_hash == key_hash, Project.is_active.is_(True)))
    if not project:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if x_project_id and str(project.id) != x_project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project scope mismatch")
    return project


async def require_admin(
    x_api_key: str | None = Header(default=None),
) -> bool:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if not _is_admin_key(x_api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin key required")
    return True


async def get_project_for_ingest(
    project: Project = Depends(get_project),
) -> Project:
    if not project.key_activated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key not provisioned for ingestion. Rotate Key first.",
        )
    return project
