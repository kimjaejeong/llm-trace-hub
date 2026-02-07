from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.db.session import get_db
from app.models import Project
from app.schemas.decision import DecideRequest
from app.services.decision_service import DecisionService


router = APIRouter(prefix="/api/v1", tags=["decision"])


@router.post("/decide")
async def decide(
    payload: DecideRequest,
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = DecisionService(db, project.id)
    return await service.decide(payload)
