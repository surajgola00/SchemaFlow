from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel


class NodeRun(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    run_id: str = Field(index=True)
    node_id: str
    status: str = Field(default="pending")  # pending|running|succeeded|failed|skipped|cancelled
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    items_in: int = Field(default=0)
    items_out: int = Field(default=0)
    error: Optional[str] = None
