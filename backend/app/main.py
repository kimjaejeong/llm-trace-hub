from fastapi import FastAPI

from app.api.cases import router as cases_router
from app.api.decisions import router as decisions_router
from app.api.evals import router as evals_router
from app.api.ingest import router as ingest_router
from app.api.policies import router as policies_router
from app.api.projects import router as projects_router
from app.api.traces import router as traces_router

app = FastAPI(title="LLM Trace Hub")

app.include_router(ingest_router)
app.include_router(evals_router)
app.include_router(traces_router)
app.include_router(policies_router)
app.include_router(decisions_router)
app.include_router(cases_router)
app.include_router(projects_router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
