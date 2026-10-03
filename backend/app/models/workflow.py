from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlmodel import Field, SQLModel


class Workflow(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    prompt: str
    target_schema: str = Field(default="[]")   # JSON string — backward compat
    execution_dag: str = Field(default="[]")    # JSON string — backward compat
    spec_json: str = Field(default="{}")        # Full WorkflowSpec JSON
    version: int = Field(default=1)
    parent_id: Optional[str] = Field(default=None)
    tags: str = Field(default="[]")             # JSON list of tag strings
    title: str = Field(default="")
    entity_type: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
