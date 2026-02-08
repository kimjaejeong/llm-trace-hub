#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
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

    trace_id = client.start_langgraph_run(
        graph_name="agent_router",
        run_id="lg-sdk-demo-001",
        input_text="환불 규정 알려줘",
        model="gpt-4.1-mini",
        environment="local",
        user_id="demo-user",
        session_id="lg-session",
    )

    # 1) Router node
    client.start_langgraph_node(
        node_id="router",
        node_name="intent_router",
        node_type="router",
        input_state={"question": "환불 규정 알려줘"},
        metadata={"team": "agent-core"},
    )
    client.flush()
    time.sleep(1.0)
    client.end_langgraph_node(
        node_id="router",
        output_state={"route": "policy_lookup"},
        token_usage={"prompt_tokens": 42, "completion_tokens": 16, "total_tokens": 58},
    )
    client.flush()
    time.sleep(1.0)

    # 2) Tool node
    client.start_langgraph_node(
        node_id="policy_lookup",
        node_name="policy_lookup",
        node_type="tool",
        parent_node_id="router",
        input_state={"route": "policy_lookup"},
        metadata={"integration": "policy_db"},
    )
    client.flush()
    time.sleep(1.0)
    client.end_langgraph_node(
        node_id="policy_lookup",
        output_state={"policy_id": "refund-v3"},
        token_usage={"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16},
    )
    client.flush()
    time.sleep(1.0)

    # 3) Response node
    client.start_langgraph_node(
        node_id="answer",
        node_name="answer_generator",
        node_type="llm",
        parent_node_id="policy_lookup",
        input_state={"policy_id": "refund-v3"},
        metadata={"prompt_template": "refund_answer_v1"},
    )
    client.flush()
    time.sleep(1.0)
    client.end_langgraph_node(
        node_id="answer",
        output_state={"answer": "구매 후 7일 이내 미사용 상태에서 환불 가능합니다."},
        token_usage={"prompt_tokens": 220, "completion_tokens": 68, "total_tokens": 288},
    )

    client.flush()
    print({"ok": True, "trace_id": trace_id})
    print(f"UI: http://localhost:3000/traces/{trace_id}")
    print("Check 1: LangGraph Live Nodes 섹션에서 노드 상태가 순차 반영되는지 확인")
    print("Check 2: LangGraph Node-Edge Graph에서 router -> policy_lookup -> answer 연결 확인")
    print("Check 3: Source 컬럼에서 mapped 상태 확인")


if __name__ == "__main__":
    main()
