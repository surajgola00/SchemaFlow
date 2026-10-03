from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    paused = "paused"
    completed = "completed"
    partial = "partial"
    failed = "failed"
    cancelled = "cancelled"


class ExecutionRun(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    workflow_id: str = Field(foreign_key="workflow.id")
    status: RunStatus = Field(default=RunStatus.queued)
    state: str = Field(default="queued")             # mirrors status for typed events
    compliance_status: str = Field(default="{}")      # JSON
    progress_pct: int = Field(default=0)
    logs: str = Field(default="[]")                   # backward compat JSON list
    budget_json: str = Field(default="{}")            # max_pages, max_records, etc.
    metrics_json: str = Field(default="{}")           # fields_extracted, verified_ratio, etc.
    engine_mode: str = Field(default="demo")          # "live" | "demo"
    llm_mode: str = Field(default="mock")             # "live" | "mock"
    use_mock: bool = Field(default=True)              # backward compat
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
