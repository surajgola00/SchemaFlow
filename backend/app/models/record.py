from datetime import datetime, timezone
from uuid import uuid4
from sqlmodel import Field, SQLModel

class ExtractedRecord(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    run_id: str = Field(foreign_key="executionrun.id")
    data: str  # JSON string
    source_url: str
    source_snippet: str
    confidence_score: float = Field(default=1.0)
    is_duplicate: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
