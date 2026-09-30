from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel

class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"

class ExecutionRun(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    workflow_id: str = Field(foreign_key="workflow.id")
    status: RunStatus = Field(default=RunStatus.queued)
    compliance_status: str = Field(default="{}")
    progress_pct: int = Field(default=0)
    logs: str = Field(default="[]")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    use_mock: bool = Field(default=True)
