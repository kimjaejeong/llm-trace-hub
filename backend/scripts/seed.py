import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Policy, PolicyVersion, Project, Span, SpanEvent, Trace


def run() -> None:
    engine = create_engine(settings.database_url)
    with Session(engine) as db:
        raw_key = "dev-key"
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        project = db.query(Project).filter(Project.api_key_hash == key_hash).first()
        if not project:
            project = Project(id=uuid.uuid4(), name="Demo Project", api_key_hash=key_hash)
            db.add(project)
            db.flush()

        trace_id = uuid.uuid4()
        start = datetime.now(timezone.utc) - timedelta(minutes=5)
        trace = Trace(
            id=trace_id,
            project_id=project.id,
            status="success",
            start_time=start,
            end_time=start + timedelta(minutes=1),
            model="gpt-4.1-mini",
            environment="dev",
            user_id="user-123",
            session_id="sess-abc",
            input_text="What are best savings strategies?",
            output_text="Diversify and keep emergency funds.",
            attributes={"team": "growth", "experiment": "eval-a"},
            total_spans=2,
            ended_spans=2,
            has_open_spans=False,
            completion_rate=1.0,
            user_review_passed=True,
        )
        db.add(trace)
        db.flush()

        root_span = Span(
            id=uuid.uuid4(),
            project_id=project.id,
            trace_id=trace_id,
            parent_span_id=None,
            name="root",
            span_type="llm",
            status="success",
            start_time=start,
            end_time=start + timedelta(seconds=30),
            attributes={"model": "gpt-4.1-mini"},
            idempotency_key=f"seed-root-{trace_id}",
        )
        child_span = Span(
            id=uuid.uuid4(),
            project_id=project.id,
            trace_id=trace_id,
            parent_span_id=root_span.id,
            name="retrieval",
            span_type="tool",
            status="success",
            start_time=start + timedelta(seconds=1),
            end_time=start + timedelta(seconds=12),
            attributes={"source": "kb"},
            idempotency_key=f"seed-child-{trace_id}",
        )
        db.add_all([root_span, child_span])

        db.add(
            SpanEvent(
                project_id=project.id,
                trace_id=trace_id,
                span_id=root_span.id,
                event_type="LOG",
                event_time=start + timedelta(seconds=2),
                payload={"message": "token usage=120"},
                idempotency_key=f"seed-log-{trace_id}",
            )
        )

        policy = db.query(Policy).filter(Policy.project_id == project.id, Policy.name == "default-safety").first()
        if not policy:
            policy = Policy(project_id=project.id, name="default-safety", description="Default safety policy")
            db.add(policy)
            db.flush()
            version = PolicyVersion(
                policy_id=policy.id,
                version=1,
                effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                active=True,
                definition={
                    "rules": [
                        {
                            "priority": 10,
                            "when": {"any": [{"field": "signals.pii", "op": "eq", "value": True}]},
                            "then": {"action": "ESCALATE", "reason_code": "PII_DETECTED", "severity": "high"},
                            "metadata": {"owner": "trust-safety"},
                        }
                    ]
                },
            )
            db.add(version)

        db.commit()
        print(f"Seeded project api key: {raw_key}")


if __name__ == "__main__":
    run()
