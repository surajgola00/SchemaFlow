from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel


class QualityReport(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    run_id: str = Field(unique=True, index=True)
    report_json: str = Field(default="{}")  # Full QualityReport dict as JSON
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
