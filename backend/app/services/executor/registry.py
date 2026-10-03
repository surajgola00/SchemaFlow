"""
RunRegistry — tracks active asyncio tasks with pause/cancel controls.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RunHandle:
    task: asyncio.Task  # type: ignore[type-arg]
    cancel_event: asyncio.Event
    pause_event: asyncio.Event


class RunRegistry:
    """Singleton in-memory registry of active workflow runs."""

    def __init__(self) -> None:
        self._handles: dict[str, RunHandle] = {}
        self._lock = asyncio.Lock()

    def register(
        self,
        run_id: str,
        task: asyncio.Task,  # type: ignore[type-arg]
        cancel_event: asyncio.Event,
        pause_event: asyncio.Event,
    ) -> None:
        self._handles[run_id] = RunHandle(
            task=task,
            cancel_event=cancel_event,
            pause_event=pause_event,
        )

    def pause(self, run_id: str) -> bool:
        """Set the pause event for a run. Returns True if found."""
        handle = self._handles.get(run_id)
        if handle:
            handle.pause_event.set()
            return True
        return False

    def resume(self, run_id: str) -> bool:
        """Clear the pause event for a run. Returns True if found."""
        handle = self._handles.get(run_id)
        if handle:
            handle.pause_event.clear()
            return True
        return False

    def cancel(self, run_id: str) -> bool:
        """Set the cancel event (and unpause if paused). Returns True if found."""
        handle = self._handles.get(run_id)
        if handle:
            handle.cancel_event.set()
            handle.pause_event.clear()  # unblock any checkpoint waits
            return True
        return False

    def remove(self, run_id: str) -> None:
        self._handles.pop(run_id, None)

    def get_handle(self, run_id: str) -> Optional[RunHandle]:
        return self._handles.get(run_id)

    def is_active(self, run_id: str) -> bool:
        return run_id in self._handles


# Module-level singleton
run_registry = RunRegistry()
