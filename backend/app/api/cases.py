from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.db.session import get_db
from app.models import Project
from app.schemas.case import CaseActionRequest
from app.services.case_service import CaseService


router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.get("")
def list_cases(
    status: str | None = Query(default=None),
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = CaseService(db, project.id)
    return service.list_cases(status)


@router.get("/{case_id}")
def get_case(
    case_id: UUID,
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = CaseService(db, project.id)
    return service.get_case(case_id)


@router.post("/{case_id}/ack")
def ack_case(
    case_id: UUID,
    payload: CaseActionRequest,
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = CaseService(db, project.id)
    return service.ack_case(case_id, payload.assignee)


@router.post("/{case_id}/resolve")
def resolve_case(
    case_id: UUID,
    payload: CaseActionRequest,
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = CaseService(db, project.id)
    return service.resolve_case(case_id, payload.assignee)
