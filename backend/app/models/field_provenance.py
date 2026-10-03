from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel


class FieldProvenance(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    record_id: str = Field(index=True)
    field_name: str
    value: Optional[str] = None
    evidence_text: str = Field(default="")
    evidence_start: int = Field(default=-1)
    evidence_end: int = Field(default=-1)
    source_url: str = Field(default="")
    source_doc_id: Optional[str] = None
    confidence: float = Field(default=0.0)
    verified: bool = Field(default=False)
