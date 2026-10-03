"""
Base class for DAG execution nodes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from app.schemas.workflow import DagNode
from app.services.executor.context import RunContext


@dataclass
class NodeResult:
    status: Literal["succeeded", "failed", "skipped", "cancelled"]
    items_in: int = 0
    items_out: int = 0
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


class BaseNode(ABC):
    node_type: str

    @abstractmethod
    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        ...
