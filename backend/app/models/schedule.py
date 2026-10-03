from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel


class Schedule(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    workflow_id: str = Field(index=True)
    cron_expression: str
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_run_at: Optional[datetime] = None
    last_run_id: Optional[str] = None
    label: str = Field(default="")


class RecordFeedback(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    record_id: str = Field(index=True)
    feedback_type: str  # "wrong" | "correct" | "duplicate"
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
