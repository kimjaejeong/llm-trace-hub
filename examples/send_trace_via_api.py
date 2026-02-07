#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = os.getenv("TRACEHUB_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("TRACEHUB_API_KEY", "dev-key")


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def post_or_raise(client: httpx.Client, url: str, headers: dict, payload: dict) -> None:
    res = client.post(url, headers=headers, json=payload)
    if res.status_code >= 400:
        raise RuntimeError(f"{res.status_code} {url} -> {res.text}")


def main() -> None:
    headers = {"x-api-key": API_KEY, "content-type": "application/json"}

    with httpx.Client(timeout=10.0) as client:
        for attempt in range(1, 6):
            trace_id = str(uuid.uuid4())
            root_span_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            trace_payload = {
                "trace": {
                    "trace_id": trace_id,
                    "status": "running",
                    "start_time": iso(now),
                    "model": "gpt-4.1-mini",
                    "environment": "local",
                    "user_id": "demo-user",
                    "session_id": "demo-session",
                    "input_text": "트레이싱 테스트 질문",
                    "attributes": {"source": "examples/send_trace_via_api.py"},
                },
                "spans": [
                    {
                        "span_id": root_span_id,
                        "trace_id": trace_id,
                        "name": "root",
                        "span_type": "llm",
                        "status": "running",
                        "start_time": iso(now),
                        "attributes": {"phase": "start"},
                        "idempotency_key": f"{trace_id}:root:start",
                    }
                ],
            }

            events_payload = {
                "events": [
                    {
                        "trace_id": trace_id,
                        "span_id": root_span_id,
                        "event_type": "LOG",
                        "event_time": iso(now + timedelta(seconds=1)),
                        "payload": {"message": "retrieval started", "level": "info"},
                        "idempotency_key": f"{trace_id}:root:log:1",
                    },
                    {
                        "trace_id": trace_id,
                        "span_id": root_span_id,
                        "event_type": "SPAN_ENDED",
                        "event_time": iso(now + timedelta(seconds=2)),
                        "payload": {"status": "success", "error": None},
                        "idempotency_key": f"{trace_id}:root:end",
                    },
                ]
            }

            eval_payload = {
                "trace_id": trace_id,
                "eval_name": "faithfulness",
                "eval_model": "gpt-4.1-mini",
                "score": 0.88,
                "passed": True,
                "metadata": {"note": "demo eval"},
                "user_review_passed": True,
                "idempotency_key": f"eval:{trace_id}:faithfulness:1",
            }

            try:
                post_or_raise(client, f"{BASE_URL}/api/v1/ingest/traces", headers, trace_payload)
                post_or_raise(client, f"{BASE_URL}/api/v1/ingest/spans", headers, events_payload)
                post_or_raise(client, f"{BASE_URL}/api/v1/evals", headers, eval_payload)

                print(json.dumps({"ok": True, "trace_id": trace_id}, ensure_ascii=False, indent=2))
                print(f"UI: http://localhost:3000/traces/{trace_id}")
                return
            except RuntimeError as exc:
                msg = str(exc)
                if "409" in msg and attempt < 5:
                    print(f"[retry {attempt}] 409 conflict: {msg}")
                    continue
                raise

    raise RuntimeError("failed to ingest trace after retries")


if __name__ == "__main__":
    main()
