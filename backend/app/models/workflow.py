from datetime import datetime, timezone
from uuid import uuid4
from sqlmodel import Field, SQLModel

class Workflow(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    prompt: str
    target_schema: str  # JSON string
    execution_dag: str  # JSON string
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
