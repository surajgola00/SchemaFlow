"""
RunContext — holds execution state, counters, events, and cancellation/pause handles.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from app.schemas.workflow import WorkflowSpec
from app.services.llm.factory import AnyLLMClient


@dataclass
class RunContext:
    run_id: str
    workflow_id: str
    spec: WorkflowSpec
    llm: AnyLLMClient
    emit: Callable[[dict[str, Any]], None]
    cancel_event: asyncio.Event
    pause_event: asyncio.Event
    counters: dict[str, int] = field(default_factory=lambda: {"pages": 0, "records": 0, "verified": 0, "rejected": 0})
    budget: dict[str, Any] = field(default_factory=lambda: {"max_pages": 30, "max_records": 100, "max_runtime_seconds": 300})
    start_time: float = field(default_factory=time.monotonic)
    engine_mode: str = "demo"
    replay_speed: str = "fast"  # "fast" | "cinematic"
    fixture_docs: list[dict[str, Any]] = field(default_factory=list)
    fixture_records: list[dict[str, Any]] = field(default_factory=list)

    async def checkpoint(self) -> bool:
        """Call between units of work. Returns False if budget exceeded or cancelled."""
        if self.cancel_event.is_set():
            return False

        # Wait while paused
        while self.pause_event.is_set():
            await asyncio.sleep(0.2)
            if self.cancel_event.is_set():
                return False

        # Check limits
        if self.counters.get("pages", 0) >= self.budget.get("max_pages", 30):
            return False
        if self.counters.get("records", 0) >= self.budget.get("max_records", 100):
            return False
        if time.monotonic() - self.start_time > self.budget.get("max_runtime_seconds", 300):
            return False

        return True

    def emit_log(self, level: str, message: str, node_id: str = "") -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.emit({
            "type": "log",
            "level": level.upper(),
            "message": message,
            "node_id": node_id,
            "timestamp": ts,
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
        })

    def emit_node_event(self, event_type: str, node_id: str, data: dict[str, Any] | None = None) -> None:
        self.emit({
            "type": event_type,
            "node_id": node_id,
            "run_id": self.run_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        })
