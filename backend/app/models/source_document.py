from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel


class SourceDocument(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    run_id: str = Field(index=True)
    url: str = Field(default="")
    canonical_url: str = Field(default="", index=True)
    connector: str = Field(default="")
    status: str = Field(default="fetched")    # fetched|blocked|failed
    http_status: int = Field(default=200)
    content_hash: str = Field(default="", index=True)
    text: str = Field(default="")
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    blocked_reason: Optional[str] = None
