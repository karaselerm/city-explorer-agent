from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import LOG_DIR


@dataclass(slots=True)
class Metrics:
    total_requests: int = 0
    completed_requests: int = 0
    fallback_requests: int = 0
    tool_timeouts: int = 0
    tool_errors: int = 0
    last_latency_ms: int = 0


@dataclass(slots=True)
class EventLogger:
    path: Path = field(default_factory=lambda: LOG_DIR / "events.jsonl")
    metrics: Metrics = field(default_factory=Metrics)

    def log(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def begin_request(self, request_id: str) -> float:
        self.metrics.total_requests += 1
        start = time.perf_counter()
        self.log({"type": "request_start", "request_id": request_id, "ts": time.time()})
        return start

    def end_request(self, request_id: str, start: float, ok: bool, used_fallback: bool) -> None:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        self.metrics.last_latency_ms = elapsed_ms
        if ok:
            self.metrics.completed_requests += 1
        if used_fallback:
            self.metrics.fallback_requests += 1
        self.log(
            {
                "type": "request_end",
                "request_id": request_id,
                "ok": ok,
                "used_fallback": used_fallback,
                "latency_ms": elapsed_ms,
                "ts": time.time(),
            }
        )

    def log_tool(self, request_id: str, tool: str, ok: bool, latency_ms: int, error: str = "") -> None:
        if not ok:
            self.metrics.tool_errors += 1
            if "timeout" in error.lower():
                self.metrics.tool_timeouts += 1
        self.log(
            {
                "type": "tool_call",
                "request_id": request_id,
                "tool": tool,
                "ok": ok,
                "latency_ms": latency_ms,
                "error": error,
                "ts": time.time(),
            }
        )
