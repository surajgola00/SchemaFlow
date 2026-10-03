"""
WorkflowSpec Pydantic schemas — the contract between compiler, executor, and frontend.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class FieldSpec(BaseModel):
    name: str  # snake_case
    label: str
    type: Literal[
        "string", "number", "integer", "boolean", "date",
        "url", "email", "phone", "currency", "enum", "list"
    ]
    description: str  # tells the extractor exactly what to look for
    required: bool = False
    enum_values: list[str] | None = None
    unique_key: bool = False  # participates in dedup key
    validators: list[str] = Field(default_factory=list)  # e.g. ["url","min_len:2"]


class SourceStrategy(BaseModel):
    connectors: list[
        Literal[
            "web_search", "rss", "hackernews", "github",
            "wikipedia", "arxiv", "direct_urls", "sitemap"
        ]
    ]
    seed_queries: list[str]
    seed_urls: list[str] = Field(default_factory=list)
    domain_allowlist: list[str] = Field(default_factory=list)
    domain_blocklist: list[str] = Field(default_factory=list)
    rationale: str  # WHY these sources (shown in UI)


class DagNode(BaseModel):
    id: str
    type: Literal[
        "discover_sources", "fetch", "extract", "normalize",
        "validate", "dedupe", "enrich", "score", "finalize"
    ]
    depends_on: list[str] = Field(default_factory=list)
    params: dict = Field(default_factory=dict)
    label: str


class WorkflowSpec(BaseModel):
    title: str
    intent_summary: str
    entity_type: str  # e.g. "startup", "job_opening", "sales_lead"
    fields: list[FieldSpec]  # 4-12 fields
    source_strategy: SourceStrategy
    dag: list[DagNode]
    limits: dict = Field(default_factory=dict)  # max_pages, max_records, per_domain_rps
    assumptions: list[str] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)  # at most 2
    risk_notes: list[str] = Field(default_factory=list)
