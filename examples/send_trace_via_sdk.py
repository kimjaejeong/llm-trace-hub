#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

from _env import load_repo_env

ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from llm_trace_hub import LLMTraceClient


def main() -> None:
    load_repo_env()
    api_key = os.getenv("TRACEHUB_API_KEY")
    if not api_key:
        raise RuntimeError("TRACEHUB_API_KEY is required. Rotate Key in /projects first.")
    client = LLMTraceClient(base_url=os.getenv("TRACEHUB_BASE_URL", "http://localhost:8000"), api_key=api_key)

    trace_id = client.start_trace(
        name="sdk-demo-trace",
        input_text="SDK로 트레이싱 찍기",
        model="gpt-4.1-mini",
        environment="local",
        user_id="demo-user",
        session_id="sdk-session",
        attributes={"source": "examples/send_trace_via_sdk.py"},
    )

    span = client.start_span("retrieval", span_type="tool", attributes={"index": "docs"})
    client.log_event("search docs", metadata={"k": 5}, span_id=span.span_id)
    client.end_span(status="success", span_id=span.span_id)

    client.attach_eval(
        eval_name="answer_quality",
        eval_model="gpt-4.1-mini",
        score=0.91,
        passed=True,
        trace_id=trace_id,
        metadata={"judge": "demo"},
        user_review_passed=True,
    )

    client.flush()

    print({"ok": True, "trace_id": trace_id})
    print(f"UI: http://localhost:3000/traces/{trace_id}")


if __name__ == "__main__":
    main()
