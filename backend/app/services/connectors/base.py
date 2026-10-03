"""
Base connector interface and SourceDoc dataclass.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.schemas.workflow import WorkflowSpec
    from app.services.executor.context import RunContext


@dataclass
class SourceDoc:
    url: str
    title: str
    text: str
    fetched_at: datetime
    connector: str
    content_hash: str
    http_status: int = 200
    license_note: Optional[str] = None
    blocked: bool = False
    blocked_reason: Optional[str] = None


class Connector(ABC):
    name: str

    @abstractmethod
    async def discover(self, spec: Any, ctx: Any) -> list[str]:
        """Return list of candidate URLs to fetch. Does not fetch full content."""
        ...
