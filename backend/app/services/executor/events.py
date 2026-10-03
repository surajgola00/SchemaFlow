"""
Event bus for SSE streaming — backward-compatible in-memory store.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable

# Global event store — run_id -> list of event dicts
run_events: dict[str, list[dict]] = defaultdict(list)


def emit_event(run_id: str, event: dict) -> None:
    """Append an event to the run's event list."""
    run_events[run_id].append(event)


def get_emitter(run_id: str) -> Callable[[dict], None]:
    """Return a closure that emits events for a specific run."""
    def _emit(event: dict) -> None:
        emit_event(run_id, event)
    return _emit


def clear_events(run_id: str) -> None:
    """Clear all events for a run (call on cleanup)."""
    if run_id in run_events:
        del run_events[run_id]


def add_log(run_id: str, level: str, message: str, node_id: str = "") -> None:
    """Convenience: emit a log event (backward-compat format)."""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    emit_event(run_id, {
        "type": "log",
        "level": level.upper(),
        "message": message,
        "node_id": node_id,
        "timestamp": ts,
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
    })
