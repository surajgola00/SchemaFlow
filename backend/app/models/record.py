from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel


class ExtractedRecord(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    run_id: str = Field(foreign_key="executionrun.id", index=True)

    # Backward-compat fields
    data: str = Field(default="{}")           # JSON string
    source_snippet: str = Field(default="")

    # New v2 fields
    data_json: str = Field(default="{}")      # Same as data; separate col for clarity
    source_url: str = Field(default="")
    confidence_score: float = Field(default=0.0)   # backward compat
    confidence: float = Field(default=0.0)
    verification_status: str = Field(default="partial")  # verified|partial|rejected
    corroboration_count: int = Field(default=1)
    sources_json: str = Field(default="[]")  # list of {url, connector} dicts
    dedupe_key: str = Field(default="", index=True)
    is_duplicate: bool = Field(default=False)        # backward compat

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
