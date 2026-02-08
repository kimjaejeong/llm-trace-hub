from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_project_for_ingest
from app.db.session import get_db
from app.models import Project
from app.schemas.eval import EvalCreateRequest
from app.services.eval_service import EvalService


router = APIRouter(prefix="/api/v1", tags=["evals"])


@router.post("/evals")
def create_eval(
    payload: EvalCreateRequest,
    project: Project = Depends(get_project_for_ingest),
    db: Session = Depends(get_db),
):
    service = EvalService(db, project.id)
    row = service.create_eval(payload)
    return {
        "id": str(row.id),
        "trace_id": str(row.trace_id) if row.trace_id else None,
        "span_id": str(row.span_id) if row.span_id else None,
        "eval_name": row.eval_name,
        "eval_model": row.eval_model,
        "score": row.score,
        "passed": row.passed,
        "metadata": row.eval_metadata or {},
        "user_review_passed": row.user_review_passed,
        "created_at": row.created_at,
    }
