from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel


class Dataset(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    workflow_id: str = Field(unique=True, index=True)
    title: str = Field(default="")
    entity_type: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DatasetVersion(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    dataset_id: str = Field(index=True)
    version_no: int = Field(default=1)
    run_id: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    record_count: int = Field(default=0)
    quality_summary: str = Field(default="{}")  # JSON
    schema_hash: str = Field(default="")         # hash of spec fields for schema-diff
