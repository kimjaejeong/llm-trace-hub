from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.db.session import get_db
from app.models import Project
from app.services.trace_service import TraceService


router = APIRouter(prefix="/api/v1/traces", tags=["traces"])


@router.get("")
def list_traces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    status: str | None = None,
    tag: str | None = None,
    model: str | None = None,
    environment: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    search: str | None = None,
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = TraceService(db, project.id)
    return service.list_traces(
        page=page,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
        status=status,
        tag=tag,
        model=model,
        environment=environment,
        user_id=user_id,
        session_id=session_id,
        search=search,
    )


@router.get("/stats/overview")
def get_trace_stats(
    last_hours: int = Query(default=24, ge=1, le=168),
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = TraceService(db, project.id)
    return service.trace_stats(last_hours=last_hours)


@router.get("/{trace_id}")
def get_trace_detail(
    trace_id: UUID,
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = TraceService(db, project.id)
    return service.get_trace_detail(trace_id)
