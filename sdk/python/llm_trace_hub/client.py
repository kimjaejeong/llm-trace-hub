from __future__ import annotations

import contextvars
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx


_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
_current_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("span_id", default=None)


@dataclass
class SpanContext:
    trace_id: str
    span_id: str


@dataclass
class NodeContext:
    trace_id: str
    node_id: str
    span_id: str


class LLMTraceClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        batch_size: int = 20,
        flush_interval_sec: float = 1.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec
        self.max_retries = max_retries
        self._queue: list[dict[str, Any]] = []
        self._last_flush = time.time()
        self._langgraph_nodes: dict[str, str] = {}

    @staticmethod
    def _raise_with_body(res: httpx.Response) -> None:
        if res.status_code < 400:
            return
        body = res.text
        raise httpx.HTTPStatusError(
            f"{res.status_code} {res.request.method} {res.request.url} -> {body}",
            request=res.request,
            response=res,
        )

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key, "content-type": "application/json"}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _enqueue(self, event: dict[str, Any]) -> None:
        self._queue.append(event)
        should_flush = len(self._queue) >= self.batch_size or (time.time() - self._last_flush) >= self.flush_interval_sec
        if should_flush:
            self.flush()

    def flush(self) -> None:
        if not self._queue:
            return

        payload = {"events": self._queue.copy(), "allow_missing_parent": True}
        backoff = 0.5
        last_error: Exception | None = None

        for _ in range(self.max_retries):
            try:
                with httpx.Client(timeout=5.0) as client:
                    res = client.post(f"{self.base_url}/api/v1/ingest/spans", headers=self._headers(), json=payload)
                    self._raise_with_body(res)
                    self._queue.clear()
                    self._last_flush = time.time()
                    return
            except Exception as exc:
                last_error = exc
                time.sleep(backoff)
                backoff *= 2

        if last_error:
            raise last_error

    def start_trace(
        self,
        name: str,
        input_text: str | None = None,
        model: str | None = None,
        environment: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        last_error: Exception | None = None
        for _ in range(max(self.max_retries, 5)):
            trace_id = str(uuid.uuid4())
            root_span_id = str(uuid.uuid4())
            _current_trace_id.set(trace_id)
            _current_span_id.set(root_span_id)

            trace_payload = {
                "trace": {
                    "trace_id": trace_id,
                    "status": "running",
                    "start_time": self._now(),
                    "attributes": attributes or {"trace_name": name},
                    "model": model,
                    "environment": environment,
                    "user_id": user_id,
                    "session_id": session_id,
                    "input_text": input_text,
                },
                "spans": [
                    {
                        "span_id": root_span_id,
                        "trace_id": trace_id,
                        "parent_span_id": None,
                        "name": name,
                        "span_type": "root",
                        "status": "running",
                        "start_time": self._now(),
                        "attributes": attributes or {},
                        "idempotency_key": f"{trace_id}:{root_span_id}:start",
                    }
                ],
            }
            with httpx.Client(timeout=5.0) as client:
                res = client.post(f"{self.base_url}/api/v1/ingest/traces", headers=self._headers(), json=trace_payload)
                if res.status_code == 409:
                    last_error = httpx.HTTPStatusError(
                        f"409 conflict while creating trace -> {res.text}",
                        request=res.request,
                        response=res,
                    )
                    continue
                self._raise_with_body(res)
                return trace_id

        if last_error:
            raise last_error
        raise RuntimeError("failed to start trace")

    def start_span(self, name: str, span_type: str = "task", attributes: dict[str, Any] | None = None) -> SpanContext:
        trace_id = _current_trace_id.get()
        parent_id = _current_span_id.get()
        if not trace_id:
            raise RuntimeError("start_trace() must be called before start_span()")

        span_id = str(uuid.uuid4())
        _current_span_id.set(span_id)
        self._enqueue(
            {
                "trace_id": trace_id,
                "span_id": span_id,
                "event_type": "SPAN_STARTED",
                "event_time": self._now(),
                "payload": {
                    "name": name,
                    "span_type": span_type,
                    "parent_span_id": parent_id,
                    "attributes": attributes or {},
                    "status": "running",
                    "idempotency_key": f"{trace_id}:{span_id}:start",
                },
                "idempotency_key": f"{trace_id}:{span_id}:evt:start",
            }
        )
        return SpanContext(trace_id=trace_id, span_id=span_id)

    def end_span(self, status: str = "success", error: str | None = None, span_id: str | None = None) -> None:
        trace_id = _current_trace_id.get()
        sid = span_id or _current_span_id.get()
        if not trace_id or not sid:
            raise RuntimeError("no active span")
        self._enqueue(
            {
                "trace_id": trace_id,
                "span_id": sid,
                "event_type": "SPAN_ENDED",
                "event_time": self._now(),
                "payload": {"status": status, "error": error},
                "idempotency_key": f"{trace_id}:{sid}:evt:end",
            }
        )

    def log_event(self, message: str, level: str = "info", span_id: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        trace_id = _current_trace_id.get()
        sid = span_id or _current_span_id.get()
        if not trace_id:
            raise RuntimeError("no active trace")
        self._enqueue(
            {
                "trace_id": trace_id,
                "span_id": sid,
                "event_type": "LOG",
                "event_time": self._now(),
                "payload": {"message": message, "level": level, "metadata": metadata or {}},
                "idempotency_key": f"{trace_id}:{sid}:log:{uuid.uuid4()}",
            }
        )

    def attach_eval(
        self,
        eval_name: str,
        eval_model: str,
        score: float,
        passed: bool,
        trace_id: str | None = None,
        span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        user_review_passed: bool | None = None,
    ) -> None:
        tid = trace_id or _current_trace_id.get()
        if not tid and not span_id:
            raise RuntimeError("trace_id or span_id required")
        payload = {
            "trace_id": tid,
            "span_id": span_id,
            "eval_name": eval_name,
            "eval_model": eval_model,
            "score": score,
            "passed": passed,
            "metadata": metadata or {},
            "user_review_passed": user_review_passed,
            "idempotency_key": f"eval:{tid or span_id}:{eval_name}:{uuid.uuid4()}",
        }
        with httpx.Client(timeout=5.0) as client:
            res = client.post(f"{self.base_url}/api/v1/evals", headers=self._headers(), json=payload)
            self._raise_with_body(res)

    def start_langgraph_run(
        self,
        graph_name: str,
        run_id: str,
        input_text: str | None = None,
        model: str | None = None,
        environment: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        trace_id = self.start_trace(
            name=f"langgraph:{graph_name}",
            input_text=input_text,
            model=model,
            environment=environment,
            user_id=user_id,
            session_id=session_id,
            attributes={**(attributes or {}), "framework": "langgraph", "graph_name": graph_name, "run_id": run_id},
        )
        return trace_id

    def start_langgraph_node(
        self,
        node_id: str,
        node_name: str,
        node_type: str = "runnable",
        parent_node_id: str | None = None,
        input_state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> NodeContext:
        trace_id = _current_trace_id.get()
        if not trace_id:
            raise RuntimeError("start_langgraph_run() or start_trace() required")

        parent_span = self._langgraph_nodes.get(parent_node_id or "") or _current_span_id.get()
        span_id = str(uuid.uuid4())
        self._langgraph_nodes[node_id] = span_id
        self._enqueue(
            {
                "trace_id": trace_id,
                "span_id": span_id,
                "event_type": "SPAN_STARTED",
                "event_time": self._now(),
                "payload": {
                    "name": node_name,
                    "span_type": "langgraph_node",
                    "status": "running",
                    "parent_span_id": parent_span,
                    "attributes": {
                        "framework": "langgraph",
                        "node_id": node_id,
                        "node_name": node_name,
                        "node_type": node_type,
                        "input_state": input_state or {},
                        "metadata": metadata or {},
                    },
                    "idempotency_key": f"{trace_id}:{node_id}:start",
                },
                "idempotency_key": f"{trace_id}:{node_id}:evt:start",
            }
        )
        return NodeContext(trace_id=trace_id, node_id=node_id, span_id=span_id)

    def end_langgraph_node(
        self,
        node_id: str,
        status: str = "success",
        output_state: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        trace_id = _current_trace_id.get()
        if not trace_id:
            raise RuntimeError("no active trace")
        span_id = self._langgraph_nodes.get(node_id)
        if not span_id:
            raise RuntimeError(f"unknown node_id: {node_id}")

        self._enqueue(
            {
                "trace_id": trace_id,
                "span_id": span_id,
                "event_type": "EVENT",
                "event_time": self._now(),
                "payload": {
                    "node_id": node_id,
                    "output_state": output_state or {},
                    "state_keys": sorted((output_state or {}).keys()),
                },
                "idempotency_key": f"{trace_id}:{node_id}:evt:state",
            }
        )
        self.end_span(status=status, error=error, span_id=span_id)

    def ingest_langgraph_run(
        self,
        graph_name: str,
        run_id: str,
        nodes: list[dict[str, Any]],
        trace_id: str | None = None,
        status: str = "success",
        start_time: str | None = None,
        end_time: str | None = None,
        model: str | None = None,
        environment: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        input_text: str | None = None,
        output_text: str | None = None,
        attributes: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        tid = trace_id or str(uuid.uuid4())
        payload = {
            "trace_id": tid,
            "run_id": run_id,
            "graph_name": graph_name,
            "status": status,
            "start_time": start_time or self._now(),
            "end_time": end_time,
            "model": model,
            "environment": environment,
            "user_id": user_id,
            "session_id": session_id,
            "input_text": input_text,
            "output_text": output_text,
            "attributes": attributes or {},
            "tags": tags or [],
            "nodes": nodes,
            "allow_missing_parent": True,
        }
        with httpx.Client(timeout=10.0) as client:
            res = client.post(f"{self.base_url}/api/v1/ingest/langgraph-runs", headers=self._headers(), json=payload)
            res.raise_for_status()
            return res.json()

    def set_context(self, trace_id: str, span_id: str | None = None) -> None:
        _current_trace_id.set(trace_id)
        _current_span_id.set(span_id)

    def get_context(self) -> SpanContext | None:
        trace_id = _current_trace_id.get()
        if not trace_id:
            return None
        return SpanContext(trace_id=trace_id, span_id=_current_span_id.get() or "")
