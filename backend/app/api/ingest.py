from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.db.session import get_db
from app.models import Project
from app.schemas.ingest import IngestSpansRequest, IngestTraceBatchRequest
from app.services.trace_service import TraceService


router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


@router.post("/traces")
def ingest_traces(
    payload: IngestTraceBatchRequest,
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = TraceService(db, project.id)
    return service.ingest_trace_batch(payload)


@router.post("/spans")
def ingest_spans(
    payload: IngestSpansRequest,
    project: Project = Depends(get_project),
    db: Session = Depends(get_db),
):
    service = TraceService(db, project.id)
    return service.ingest_span_events(payload)
