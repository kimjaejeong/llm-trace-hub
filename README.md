# LLM Trace Hub (MVP)

Langfuse 핵심 기능에서 착안한 오픈소스 LLM Observability/Tracing + Decision Engine MVP입니다.
가장 중요한 목표인 `Trace/Span 트리 + 조회 경험`과 `LLM Judge 기반 의사결정`을 포함합니다.

## Monorepo Structure

```text
backend/        # FastAPI, SQLAlchemy, Alembic
frontend/       # Next.js (Trace/Cases UI)
sdk/python/     # Python SDK
docs/           # Architecture / ERD
docker-compose.yml
```

## 핵심 기능

- Trace/Span/Event/Eval 데이터 모델 + PostgreSQL 스키마
- Append-only 이벤트(`span_events`), 수정은 `AMENDMENT`
- Idempotency key 기반 중복 방지
- 미종료 span 감지(`has_open_spans`) + trace 완료율(`completion_rate`)
- Ingestion API (`/ingest/traces`, `/ingest/spans`, `/evals`)
- LangGraph Ingestion API (`/ingest/langgraph-runs`) for node-level tracing
- 조회 API (`/traces`, `/traces/{trace_id}` + 텍스트 검색)
- Dashboard stats API (`/traces/stats/overview`)
- Decision Engine
  - action enum: `ALLOW_ANSWER`, `BLOCK`, `ESCALATE`, `ALLOW_WITH_WARNING`, `NEED_CLARIFICATION`
  - judge span(type=`judge`) 기록 + trace 최종 decision 귀속
  - 정책 DSL(JSON/YAML), 버전/활성화 API
  - heuristic judge + llm judge plugin
  - JSON schema 강제 검증(LLM judge output)
  - `input_hash + policy_version` 캐시
- ESCALATE 케이스/알림
  - `cases`, `notifications` 테이블
  - webhook 전송
  - Cases API + UI
- AB/실험 비교 기반 필드
  - `evaluation_result`: `eval_name`, `eval_model`, `score`, `passed`, `metadata`
  - `user_review_passed` (trace/eval에 저장, UI 노출)
  - decision에 `policy_version`, `judge_model`

## 실행 방법

```bash
docker compose up --build
```

서비스:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Postgres: `localhost:5432`

시드 데이터:
- backend 컨테이너 시작 시 Alembic 마이그레이션 + seed 실행
- 기본 API key: `dev-key`

## 인증

모든 API 요청 헤더:

```http
x-api-key: dev-key
```

## API 예제

### 1) Trace + Spans 배치 수집

`POST /api/v1/ingest/traces`

```bash
curl -X POST http://localhost:8000/api/v1/ingest/traces \
  -H 'x-api-key: dev-key' -H 'content-type: application/json' \
  -d '{
    "trace": {
      "trace_id": "11111111-1111-1111-1111-111111111111",
      "status": "running",
      "start_time": "2026-02-07T10:00:00Z",
      "model": "gpt-4.1-mini",
      "environment": "prod",
      "user_id": "u-1",
      "session_id": "s-1",
      "input_text": "질문",
      "output_text": "답변",
      "attributes": {"team": "search"},
      "user_review_passed": true
    },
    "spans": [
      {
        "span_id": "22222222-2222-2222-2222-222222222222",
        "trace_id": "11111111-1111-1111-1111-111111111111",
        "name": "root",
        "span_type": "llm",
        "status": "running",
        "start_time": "2026-02-07T10:00:01Z",
        "attributes": {"model": "gpt-4.1-mini"},
        "idempotency_key": "trace-111-root-start"
      }
    ],
    "allow_missing_parent": true
  }'
```

### 2) Span 이벤트 단위 수집

`POST /api/v1/ingest/spans`

```bash
curl -X POST http://localhost:8000/api/v1/ingest/spans \
  -H 'x-api-key: dev-key' -H 'content-type: application/json' \
  -d '{
    "events": [
      {
        "trace_id": "11111111-1111-1111-1111-111111111111",
        "span_id": "22222222-2222-2222-2222-222222222222",
        "event_type": "LOG",
        "event_time": "2026-02-07T10:00:05Z",
        "payload": {"message": "tool started"},
        "idempotency_key": "log-1"
      },
      {
        "trace_id": "11111111-1111-1111-1111-111111111111",
        "span_id": "22222222-2222-2222-2222-222222222222",
        "event_type": "AMENDMENT",
        "event_time": "2026-02-07T10:00:10Z",
        "payload": {"patch": {"attributes": {"retry": 1}}},
        "idempotency_key": "amd-1"
      }
    ]
  }'
```

### 2-1) LangGraph Run/Node 수집

`POST /api/v1/ingest/langgraph-runs`

```bash
curl -X POST http://localhost:8000/api/v1/ingest/langgraph-runs \
  -H 'x-api-key: dev-key' -H 'content-type: application/json' \
  -d '{
    "trace_id": "33333333-3333-3333-3333-333333333333",
    "run_id": "lg-run-001",
    "graph_name": "agent_router",
    "status": "success",
    "start_time": "2026-02-07T10:00:00Z",
    "end_time": "2026-02-07T10:00:04Z",
    "model": "gpt-4.1-mini",
    "environment": "prod",
    "nodes": [
      {
        "node_id": "plan",
        "node_name": "planner",
        "node_type": "router",
        "start_time": "2026-02-07T10:00:00Z",
        "end_time": "2026-02-07T10:00:01Z",
        "input_state": {"question": "..." },
        "output_state": {"route": "retrieval"},
        "idempotency_key": "plan-1"
      },
      {
        "node_id": "retrieve",
        "node_name": "retrieval",
        "node_type": "tool",
        "parent_node_id": "plan",
        "start_time": "2026-02-07T10:00:01Z",
        "end_time": "2026-02-07T10:00:03Z",
        "input_state": {"route": "retrieval"},
        "output_state": {"docs": 5},
        "idempotency_key": "retrieve-1"
      }
    ]
  }'
```

### 3) Eval attach

`POST /api/v1/evals`

```bash
curl -X POST http://localhost:8000/api/v1/evals \
  -H 'x-api-key: dev-key' -H 'content-type: application/json' \
  -d '{
    "trace_id": "11111111-1111-1111-1111-111111111111",
    "eval_name": "faithfulness",
    "eval_model": "gpt-4.1-mini",
    "score": 0.78,
    "passed": true,
    "metadata": {"prompt_version": "v2"},
    "user_review_passed": true,
    "idempotency_key": "eval-1"
  }'
```

### 4) Trace 목록 조회 + 검색

`GET /api/v1/traces?status=running&model=gpt-4.1-mini&search=tool&page=1&page_size=20`

### 5) Trace 상세 조회

`GET /api/v1/traces/{trace_id}`

반환: span tree + timeline + evals + decision history + judge runs

### 5-1) 대시보드 통계 조회

`GET /api/v1/traces/stats/overview?last_hours=24`

### 6) 정책 생성/조회/활성화

```bash
curl -X POST http://localhost:8000/api/v1/policies \
  -H 'x-api-key: dev-key' -H 'content-type: application/json' \
  -d '{
    "name": "default-safety",
    "description": "Safety baseline",
    "effective_from": "2026-01-01T00:00:00Z",
    "active": true,
    "definition": {
      "rules": [
        {
          "priority": 10,
          "when": {"any": [{"field": "signals.pii", "op": "eq", "value": true}]},
          "then": {"action": "ESCALATE", "reason_code": "PII_DETECTED", "severity": "high"},
          "metadata": {"owner": "trust-safety"}
        }
      ]
    }
  }'
```

- `GET /api/v1/policies`
- `GET /api/v1/policies/{policy_id}/versions`
- `POST /api/v1/policies/{policy_id}/activate?version=2`

### 7) 의사결정 실행

`POST /api/v1/decide`

```bash
curl -X POST http://localhost:8000/api/v1/decide \
  -H 'x-api-key: dev-key' -H 'content-type: application/json' \
  -d '{
    "trace_id": "11111111-1111-1111-1111-111111111111",
    "request_payload": {"safety": {"content_filter": "ok"}},
    "response_payload": {"tokens": 512, "latency_ms": 900, "model": "gpt-4.1-mini"},
    "idempotency_key": "decide-1"
  }'
```

- decision 저장: `trace_decisions`
- latest snapshot: `traces.decision`
- judge 실행 기록: `judge_runs` + `span(type=judge)`
- ESCALATE면 case 생성 + webhook notification

### 8) 케이스 관리 API

- `GET /api/v1/cases?status=open`
- `GET /api/v1/cases/{case_id}`
- `POST /api/v1/cases/{case_id}/ack`
- `POST /api/v1/cases/{case_id}/resolve`

## Python SDK 사용 예

```python
from llm_trace_hub import LLMTraceClient

client = LLMTraceClient(base_url="http://localhost:8000", api_key="dev-key")

trace_id = client.start_trace(
    name="chat-request",
    input_text="원금 보장 투자 추천해줘",
    model="gpt-4.1-mini",
    environment="prod",
    user_id="user-42",
    session_id="session-1",
)

span = client.start_span("retrieval", span_type="tool", attributes={"source": "kb"})
client.log_event("retrieved 5 docs", metadata={"k": 5})
client.end_span(status="success", span_id=span.span_id)

client.attach_eval(
    eval_name="faithfulness",
    eval_model="gpt-4.1-mini",
    score=0.72,
    passed=True,
    trace_id=trace_id,
    user_review_passed=True,
)

client.flush()
```

LangGraph node-level 예제:

```python
trace_id = client.start_langgraph_run(
    graph_name="agent_router",
    run_id="lg-run-002",
    input_text="환불 규정 알려줘",
    model="gpt-4.1-mini",
)

client.start_langgraph_node(
    node_id="router",
    node_name="intent_router",
    node_type="router",
    input_state={"question": "환불 규정 알려줘"},
)
client.end_langgraph_node(
    node_id="router",
    output_state={"route": "policy_lookup"},
)

client.start_langgraph_node(
    node_id="policy_lookup",
    node_name="policy_lookup",
    node_type="tool",
    parent_node_id="router",
    input_state={"route": "policy_lookup"},
)
client.end_langgraph_node(
    node_id="policy_lookup",
    output_state={"policy_id": "refund-v3"},
)
client.flush()
```

SDK 제공 기능:
- `start_trace()`, `start_span()`, `end_span()`, `log_event()`, `attach_eval()`
- `start_langgraph_run()`, `start_langgraph_node()`, `end_langgraph_node()`, `ingest_langgraph_run()`
- context propagation (`trace_id/span_id`)
- batch flush + retry/backoff

## 프론트엔드 화면

- `/` Trace List: 필터 + 테이블 + 페이지네이션 정보
- `/` Trace Dashboard: KPI cards + 필터 + decision/langgraph visibility
- `/traces/{trace_id}` Trace Detail: span tree + timeline + langgraph node panel + eval/decision 표시
- `/cases` Cases 목록
- `/cases/{case_id}` Cases 상세 + ack/resolve

## 데이터 모델/ERD/인덱스

`docs/ARCHITECTURE.md` 참고.

## 로컬 개발 (개별 실행)

### Backend

```bash
cd backend
pip install -e .
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
BACKEND_URL=http://localhost:8000 API_KEY=dev-key npm run dev
```

### SDK

```bash
cd sdk/python
pip install -e .
```

## 빠른 트레이싱 테스트 코드

API 직접 호출:

```bash
pip install httpx
python examples/send_trace_via_api.py
```

SDK 호출:

```bash
pip install -e sdk/python
python examples/send_trace_via_sdk.py
```

## 주의

- MVP 특성상 인증은 project API key 단일 방식입니다.
- LLM Judge는 기본적으로 stub이며, endpoint를 연결하면 외부 judge 모델 호출이 가능합니다.
