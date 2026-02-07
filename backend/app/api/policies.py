from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.db.session import get_db
from app.models import Project
from app.schemas.policy import PolicyCreateRequest
from app.services.policy_service import PolicyService


router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


@router.post("")
def create_policy(
    payload: PolicyCreateRequest,
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = PolicyService(db, project.id)
    policy, version = service.create_policy(payload)
    return {"policy": policy, "version": version}


@router.get("")
def list_policies(
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = PolicyService(db, project.id)
    return service.list_policies()


@router.get("/{policy_id}/versions")
def list_policy_versions(
    policy_id: UUID,
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = PolicyService(db, project.id)
    return service.get_versions(policy_id)


@router.post("/{policy_id}/activate")
def activate_policy(
    policy_id: UUID,
    version: int = Query(..., ge=1),
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = PolicyService(db, project.id)
    return service.activate(policy_id, version)
