from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import Policy, PolicyVersion
from app.schemas.policy import PolicyCreateRequest


class PolicyService:
    def __init__(self, db: Session, project_id: UUID):
        self.db = db
        self.project_id = project_id

    def create_policy(self, payload: PolicyCreateRequest) -> tuple[Policy, PolicyVersion]:
        policy = Policy(project_id=self.project_id, name=payload.name, description=payload.description)
        self.db.add(policy)
        self.db.flush()

        version = PolicyVersion(
            policy_id=policy.id,
            version=1,
            effective_from=payload.effective_from,
            active=payload.active,
            definition=payload.definition,
        )

        if payload.active:
            self.db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy.id).update({"active": False})

        self.db.add(version)
        self.db.commit()
        self.db.refresh(policy)
        self.db.refresh(version)
        return policy, version

    def list_policies(self) -> list[Policy]:
        return self.db.scalars(select(Policy).where(Policy.project_id == self.project_id).order_by(Policy.created_at.desc())).all()

    def get_versions(self, policy_id: UUID) -> list[PolicyVersion]:
        policy = self.db.scalar(select(Policy).where(and_(Policy.id == policy_id, Policy.project_id == self.project_id)))
        if not policy:
            raise HTTPException(status_code=404, detail="policy not found")
        return self.db.scalars(
            select(PolicyVersion).where(PolicyVersion.policy_id == policy_id).order_by(PolicyVersion.version.desc())
        ).all()

    def activate(self, policy_id: UUID, version: int) -> PolicyVersion:
        policy = self.db.scalar(select(Policy).where(and_(Policy.id == policy_id, Policy.project_id == self.project_id)))
        if not policy:
            raise HTTPException(status_code=404, detail="policy not found")

        target = self.db.scalar(
            select(PolicyVersion).where(and_(PolicyVersion.policy_id == policy_id, PolicyVersion.version == version))
        )
        if not target:
            raise HTTPException(status_code=404, detail="policy version not found")

        self.db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy_id).update({"active": False})
        target.active = True
        self.db.commit()
        self.db.refresh(target)
        return target

    def get_active_version(self, force_policy_id: UUID | None = None, force_version: int | None = None) -> PolicyVersion | None:
        if force_policy_id and force_version:
            return self.db.scalar(
                select(PolicyVersion).where(
                    and_(PolicyVersion.policy_id == force_policy_id, PolicyVersion.version == force_version)
                )
            )

        if force_policy_id:
            return self.db.scalar(
                select(PolicyVersion)
                .where(and_(PolicyVersion.policy_id == force_policy_id, PolicyVersion.active.is_(True)))
                .order_by(PolicyVersion.version.desc())
            )

        return self.db.scalar(
            select(PolicyVersion)
            .join(Policy, Policy.id == PolicyVersion.policy_id)
            .where(and_(Policy.project_id == self.project_id, PolicyVersion.active.is_(True), PolicyVersion.effective_from <= datetime.utcnow()))
            .order_by(PolicyVersion.effective_from.desc(), PolicyVersion.version.desc())
        )
