import hashlib

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project


async def get_project(
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Project:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    key_hash = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    project = db.scalar(select(Project).where(Project.api_key_hash == key_hash))
    if not project:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return project
