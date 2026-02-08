from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.schemas.project import ProjectCreateIn, ProjectCreateOut, ProjectCurrentKeyOut, ProjectListItem
from app.services.project_service import ProjectService


router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectListItem], dependencies=[Depends(require_admin)])
def list_projects(
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.list_projects()


@router.post("", response_model=ProjectCreateOut, dependencies=[Depends(require_admin)])
def create_project(
    payload: ProjectCreateIn,
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.create_project(payload.name)


@router.post("/{project_id}/rotate-key", response_model=ProjectCreateOut, dependencies=[Depends(require_admin)])
def rotate_project_key(
    project_id: UUID,
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.rotate_project_key(project_id)


@router.get("/{project_id}/current-key", response_model=ProjectCurrentKeyOut, dependencies=[Depends(require_admin)])
def get_current_key(
    project_id: UUID,
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.get_current_key(project_id)


@router.post("/{project_id}/deactivate", dependencies=[Depends(require_admin)])
def deactivate_project(
    project_id: UUID,
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.set_project_active(project_id, False)


@router.post("/{project_id}/activate", dependencies=[Depends(require_admin)])
def activate_project(
    project_id: UUID,
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.set_project_active(project_id, True)


@router.delete("/{project_id}", dependencies=[Depends(require_admin)])
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.set_project_active(project_id, False)
