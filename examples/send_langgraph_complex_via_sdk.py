#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

from _env import load_repo_env

ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from llm_trace_hub import LLMTraceClient

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


def llm_step(prompt: str, model: str) -> tuple[str, dict[str, int]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if OpenAI and api_key:
        client = OpenAI(api_key=api_key)
        res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert agent node."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        text = (res.choices[0].message.content or "").strip()
        usage = {
            "prompt_tokens": int(getattr(res.usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(res.usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(res.usage, "total_tokens", 0) or 0),
        }
        return text, usage

    fallback = f"[mocked-llm] {prompt[:120]}"
    est_prompt = max(10, len(prompt) // 4)
    est_completion = max(20, len(fallback) // 4)
    return fallback, {"prompt_tokens": est_prompt, "completion_tokens": est_completion, "total_tokens": est_prompt + est_completion}


def run_node(
    client: LLMTraceClient,
    *,
    node_id: str,
    node_name: str,
    node_type: str,
    parent_node_id: str | None,
    input_state: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    llm_prompt: str | None = None,
    llm_model: str = "gpt-4.1-mini",
) -> dict[str, Any]:
    started = time.perf_counter()
    client.start_langgraph_node(
        node_id=node_id,
        node_name=node_name,
        node_type=node_type,
        parent_node_id=parent_node_id,
        input_state=input_state,
        metadata=metadata or {},
    )
    client.flush()

    if llm_prompt:
        text, usage = llm_step(llm_prompt, llm_model)
        output_state = {"result": text}
    else:
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        output_state = {"result": f"{node_name} done"}

    duration_ms = int((time.perf_counter() - started) * 1000)
    client.end_langgraph_node(
        node_id=node_id,
        output_state=output_state,
        token_usage=usage,
        duration_ms=duration_ms,
    )
    client.flush()
    time.sleep(0.8)
    return output_state


def main() -> None:
    load_repo_env()
    api_key = os.getenv("TRACEHUB_API_KEY")
    if not api_key:
        raise RuntimeError("TRACEHUB_API_KEY is required. Rotate Key in /projects first.")
    client = LLMTraceClient(base_url=os.getenv("TRACEHUB_BASE_URL", "http://localhost:8000"), api_key=api_key)
    trace_id = client.start_langgraph_run(
        graph_name="complex_refund_agent",
        run_id=f"lg-complex-{int(time.time())}",
        input_text="구매 9일째인데 환불 가능한지, 계정 상태랑 주문 내역도 함께 확인해줘",
        model="gpt-4.1-mini",
        environment=os.getenv("TRACE_ENV", "local"),
        user_id="demo-user",
        session_id="complex-session",
        attributes={"scenario": "complex", "source": "examples/send_langgraph_complex_via_sdk.py"},
    )

    input_state = {"user_query": "구매 9일째인데 환불 가능한지, 계정 상태랑 주문 내역도 함께 확인해줘"}

    guard = run_node(
        client,
        node_id="input_guard",
        node_name="input_guard",
        node_type="policy",
        parent_node_id=None,
        input_state=input_state,
        llm_prompt="Classify risk and policy concern for the user request.",
    )
    rewrite = run_node(
        client,
        node_id="query_rewriter",
        node_name="query_rewriter",
        node_type="llm",
        parent_node_id="input_guard",
        input_state={**input_state, "guard": guard["result"]},
        llm_prompt="Rewrite request into precise retrieval queries for policy + order DB.",
    )
    web_retrieval = run_node(
        client,
        node_id="retrieval_web",
        node_name="retrieval_web",
        node_type="tool",
        parent_node_id="query_rewriter",
        input_state={"query": rewrite["result"]},
        metadata={"tool": "web-index"},
    )
    order_retrieval = run_node(
        client,
        node_id="retrieval_order_db",
        node_name="retrieval_order_db",
        node_type="tool",
        parent_node_id="query_rewriter",
        input_state={"query": rewrite["result"]},
        metadata={"tool": "order-db"},
    )
    ranker = run_node(
        client,
        node_id="evidence_ranker",
        node_name="evidence_ranker",
        node_type="llm",
        parent_node_id="retrieval_web",
        input_state={"web": web_retrieval["result"], "order": order_retrieval["result"]},
        llm_prompt="Rank evidence reliability and summarize policy constraints.",
    )
    planner = run_node(
        client,
        node_id="action_planner",
        node_name="action_planner",
        node_type="llm",
        parent_node_id="evidence_ranker",
        input_state={"evidence": ranker["result"]},
        llm_prompt="Create execution plan with steps and required tools.",
    )
    sql_tool = run_node(
        client,
        node_id="sql_executor",
        node_name="sql_executor",
        node_type="tool",
        parent_node_id="action_planner",
        input_state={"plan": planner["result"]},
        metadata={"tool": "warehouse-sql"},
    )
    summary = run_node(
        client,
        node_id="answer_generator",
        node_name="answer_generator",
        node_type="llm",
        parent_node_id="sql_executor",
        input_state={"sql": sql_tool["result"], "policy": ranker["result"]},
        llm_prompt="Generate final answer with explicit policy references and confidence.",
    )
    run_node(
        client,
        node_id="safety_reviewer",
        node_name="safety_reviewer",
        node_type="judge",
        parent_node_id="answer_generator",
        input_state={"draft_answer": summary["result"]},
        llm_prompt="Check for policy violation and hallucination risk. Return PASS/BLOCK with rationale.",
    )

    client.flush()
    print({"ok": True, "trace_id": trace_id})
    print(f"UI Trace: http://localhost:3000/traces/{trace_id}")
    print("Node graph and node detail pages should show step-by-step updates, duration, and token usage.")


if __name__ == "__main__":
    main()
