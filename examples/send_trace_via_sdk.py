#!/usr/bin/env python3
from __future__ import annotations

from llm_trace_hub import LLMTraceClient


def main() -> None:
    client = LLMTraceClient(base_url="http://localhost:8000", api_key="dev-key")

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
