# LLM Trace Hub MVP Architecture

## Monorepo
- `backend/`: FastAPI + SQLAlchemy + Alembic
- `frontend/`: Next.js App Router
- `sdk/python/`: Python SDK

## Core Entities
- `projects`: API key scoped tenant.
- `traces`: top-level execution unit.
- `spans`: hierarchical units linked by `trace_id`, `parent_span_id`.
- `span_events`: append-only events (`SPAN_STARTED`, `SPAN_ENDED`, `LOG`, `EVENT`, `AMENDMENT`).
- `evaluations`: eval results attached to trace/span.
- `trace_decisions`: decision engine outputs and versioned runs.
- `policies`, `policy_versions`: JSON/YAML DSL policy definitions.
- `judge_runs`: explicit judge execution logs.
- `cases`: escalation case records.
- `notifications`: webhook delivery logs.

## ERD (Mermaid)
```mermaid
erDiagram
  projects ||--o{ traces : owns
  traces ||--o{ spans : has
  spans ||--o{ spans : parent_child
  spans ||--o{ span_events : emits
  traces ||--o{ evaluations : evaluated
  spans ||--o{ evaluations : evaluated
  traces ||--o{ trace_decisions : decided
  policies ||--o{ policy_versions : versions
  traces ||--o{ judge_runs : judged
  traces ||--o{ cases : escalated
  cases ||--o{ notifications : notifies

  projects {
    uuid id PK
    text name
    text api_key_hash
    timestamptz created_at
  }

  traces {
    uuid id PK
    uuid project_id FK
    text external_trace_id
    text status
    timestamptz start_time
    timestamptz end_time
    jsonb attributes
    text model
    text environment
    text user_id
    text session_id
    text input_text
    text output_text
    boolean has_open_spans
    integer total_spans
    integer ended_spans
    numeric completion_rate
    jsonb decision
    boolean user_review_passed
    timestamptz created_at
  }

  spans {
    uuid id PK
    uuid project_id FK
    uuid trace_id FK
    uuid parent_span_id FK
    text name
    text span_type
    text status
    timestamptz start_time
    timestamptz end_time
    text error
    jsonb attributes
    text idempotency_key
    timestamptz created_at
  }

  span_events {
    uuid id PK
    uuid project_id FK
    uuid trace_id FK
    uuid span_id FK
    text event_type
    timestamptz event_time
    jsonb payload
    text idempotency_key
    timestamptz created_at
  }

  evaluations {
    uuid id PK
    uuid project_id FK
    uuid trace_id FK
    uuid span_id FK
    text eval_name
    text eval_model
    numeric score
    boolean passed
    jsonb metadata
    boolean user_review_passed
    text idempotency_key
    timestamptz created_at
  }

  trace_decisions {
    uuid id PK
    uuid project_id FK
    uuid trace_id FK
    text action
    text reason_code
    text severity
    numeric confidence
    text policy_version
    text judge_model
    jsonb signals
    text rationale
    text idempotency_key
    timestamptz created_at
  }

  policies {
    uuid id PK
    uuid project_id FK
    text name
    text description
    timestamptz created_at
  }

  policy_versions {
    uuid id PK
    uuid policy_id FK
    integer version
    timestamptz effective_from
    boolean active
    jsonb definition
    timestamptz created_at
  }

  judge_runs {
    uuid id PK
    uuid project_id FK
    uuid trace_id FK
    uuid span_id FK
    text provider
    text model
    text action
    text reason_code
    numeric confidence
    jsonb output
    timestamptz created_at
  }

  cases {
    uuid id PK
    uuid project_id FK
    uuid trace_id FK
    text reason_code
    text status
    text assignee
    timestamptz acknowledged_at
    timestamptz resolved_at
    timestamptz created_at
  }

  notifications {
    uuid id PK
    uuid project_id FK
    uuid case_id FK
    text channel
    text target_url
    text status
    jsonb payload
    text response_snippet
    timestamptz created_at
  }
```

## Index Strategy
- `traces(project_id, start_time desc)` for list pagination.
- `traces(project_id, status, start_time desc)` for state filtering.
- `traces(project_id, environment, model, user_id, session_id)` composite filtering.
- `GIN` indexes on `traces.attributes` and `spans.attributes`.
- Full-text (`to_tsvector`) index on `traces.input_text`, `traces.output_text`, `span_events.payload->>'message'`.
- Unique constraints for idempotency:
  - `spans(project_id, idempotency_key)`
  - `span_events(project_id, idempotency_key)`
  - `evaluations(project_id, idempotency_key)`
  - `trace_decisions(project_id, idempotency_key)`

## Append-only Principle
- Raw event streams are immutable in `span_events`.
- State tables (`spans`, `traces`) are derived for query speed.
- Corrections are represented via `AMENDMENT` events with patch payload and optional state projection update.

## Decision Engine Pipeline
1. Load active policy version.
2. Execute heuristic provider.
3. If heuristic gives strong `BLOCK`/`ESCALATE`, short-circuit LLM judge.
4. Else execute LLM judge plugin (JSON schema validated).
5. Evaluate policy rules against request/response/eval/safety signals.
6. Persist:
   - `judge_runs`
   - a `judge` span + events
   - `trace_decisions`
   - `traces.decision` latest snapshot
7. If action = `ESCALATE`, open `cases` and trigger webhook notification.

## Policy DSL (JSON/YAML)
```yaml
policy_id: default-safety
version: 1
effective_from: 2026-01-01T00:00:00Z
rules:
  - priority: 10
    when:
      any:
        - field: "signals.pii"
          op: "eq"
          value: true
        - field: "evals.faithfulness.score"
          op: "lt"
          value: 0.3
    then:
      action: "ESCALATE"
      reason_code: "SAFETY_HIGH_RISK"
      severity: "high"
    metadata:
      owner: "trust-safety"
```
