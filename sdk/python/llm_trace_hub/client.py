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
                    res.raise_for_status()
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
            res.raise_for_status()
        return trace_id

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
            res.raise_for_status()

    def set_context(self, trace_id: str, span_id: str | None = None) -> None:
        _current_trace_id.set(trace_id)
        _current_span_id.set(span_id)

    def get_context(self) -> SpanContext | None:
        trace_id = _current_trace_id.get()
        if not trace_id:
            return None
        return SpanContext(trace_id=trace_id, span_id=_current_span_id.get() or "")
