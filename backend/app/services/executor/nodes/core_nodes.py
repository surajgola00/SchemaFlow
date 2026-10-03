"""
DAG execution nodes for discovery, fetch, extraction, normalisation, validation, deduplication, scoring, and finalisation.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlmodel import Session

from app.database import engine
from app.models.field_provenance import FieldProvenance
from app.models.quality import QualityReport
from app.models.record import ExtractedRecord
from app.models.run import ExecutionRun, RunStatus
from app.models.source_document import SourceDocument
from app.schemas.workflow import DagNode
from app.services.connectors.registry import get_connector
from app.services.crawler.fetcher import fetcher
from app.services.extraction.chunker import split_into_chunks
from app.services.extraction.extractor import extract_from_chunk
from app.services.extraction.verifier import verify_candidate
from app.services.executor.context import RunContext
from app.services.executor.nodes.base import BaseNode, NodeResult
from app.services.quality.dedupe import deduplicate_records
from app.services.quality.normalizers import apply_normalizers
from app.services.quality.quality_report import quality_reporter
from app.services.quality.validators import run_validators


class DiscoverSourcesNode(BaseNode):
    node_type = "discover_sources"

    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        ctx.emit_log("INFO", f"Discovering sources for {ctx.spec.entity_type}...", node_id=node.id)

        if ctx.engine_mode == "demo" and getattr(ctx, "fixture_docs", None):
            urls = [d["url"] for d in ctx.fixture_docs if d.get("url")]
            ctx.emit_log("INFO", f"Demo Replay: discovered {len(urls)} fixture URLs", node_id=node.id)
            return NodeResult(
                status="succeeded",
                items_in=len(ctx.spec.source_strategy.connectors),
                items_out=len(urls),
                data={"urls": urls},
            )

        connectors = ctx.spec.source_strategy.connectors
        urls = []

        for c_name in connectors:
            if not await ctx.checkpoint():
                break
            conn = get_connector(c_name)
            if conn:
                try:
                    found = await conn.discover(ctx.spec, ctx)
                    ctx.emit_log("INFO", f"Connector '{c_name}' discovered {len(found)} candidate URLs", node_id=node.id)
                    for u in found:
                        if u not in urls:
                            urls.append(u)
                except Exception as e:
                    ctx.emit_log("WARNING", f"Connector '{c_name}' error: {e}", node_id=node.id)

        ctx.emit_log("SUCCESS", f"Total {len(urls)} source URLs discovered", node_id=node.id)
        return NodeResult(
            status="succeeded",
            items_in=len(connectors),
            items_out=len(urls),
            data={"urls": urls},
        )


class FetchNode(BaseNode):
    node_type = "fetch"

    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        if ctx.engine_mode == "demo" and getattr(ctx, "fixture_docs", None):
            docs: list[dict[str, Any]] = []
            for d in ctx.fixture_docs:
                if not await ctx.checkpoint():
                    break
                doc_dict = {
                    "id": str(uuid4()),
                    "url": d.get("url", ""),
                    "title": d.get("title", d.get("url", "")),
                    "text": d.get("text", ""),
                    "http_status": 200,
                    "content_hash": d.get("content_hash", ""),
                }
                docs.append(doc_dict)
                with Session(engine) as session:
                    s_doc = SourceDocument(
                        id=doc_dict["id"],
                        run_id=ctx.run_id,
                        url=doc_dict["url"],
                        canonical_url=doc_dict["url"],
                        connector="fixture_replay",
                        status="fetched",
                        http_status=200,
                        content_hash=doc_dict["content_hash"],
                        text=doc_dict["text"][:1000],
                    )
                    session.add(s_doc)
                    session.commit()
                ctx.emit({
                    "type": "record_added",
                    "node_id": node.id,
                    "run_id": ctx.run_id,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "data": {"url": doc_dict["url"], "title": doc_dict["title"]},
                })
            ctx.emit_log("SUCCESS", f"Demo Replay: loaded {len(docs)} readable pages offline", node_id=node.id)
            return NodeResult(
                status="succeeded",
                items_in=len(docs),
                items_out=len(docs),
                data={"docs": docs},
            )

        candidate_urls = inputs.get("urls", [])
        ctx.emit_log("INFO", f"Fetching up to {len(candidate_urls)} discovered pages...", node_id=node.id)
        docs = []

        for i, url in enumerate(candidate_urls):
            if not await ctx.checkpoint():
                break

            result = await fetcher.fetch(url, ctx)
            if result and not result.blocked:
                doc_dict = {
                    "id": str(uuid4()),
                    "url": result.url,
                    "title": result.title,
                    "text": result.text,
                    "http_status": result.http_status,
                    "content_hash": result.content_hash,
                }
                docs.append(doc_dict)

                # Persist SourceDocument
                with Session(engine) as session:
                    s_doc = SourceDocument(
                        id=doc_dict["id"],
                        run_id=ctx.run_id,
                        url=result.url,
                        canonical_url=result.url,
                        connector="fetcher",
                        status="fetched",
                        http_status=result.http_status,
                        content_hash=result.content_hash,
                        text=result.text[:1000],
                    )
                    session.add(s_doc)
                    session.commit()

                ctx.emit({
                    "type": "record_added",
                    "node_id": node.id,
                    "run_id": ctx.run_id,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "data": {"url": result.url, "title": result.title},
                })
            else:
                with Session(engine) as session:
                    s_doc = SourceDocument(
                        run_id=ctx.run_id,
                        url=url,
                        connector="fetcher",
                        status="blocked",
                        blocked_reason="SSRF, robots.txt, or HTTP error",
                    )
                    session.add(s_doc)
                    session.commit()

        ctx.emit_log("SUCCESS", f"Successfully fetched {len(docs)} readable pages", node_id=node.id)
        return NodeResult(
            status="succeeded",
            items_in=len(candidate_urls),
            items_out=len(docs),
            data={"docs": docs},
        )


class ExtractNode(BaseNode):
    node_type = "extract"

    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        docs = inputs.get("docs", [])
        ctx.emit_log("INFO", f"Extracting entities across {len(docs)} documents...", node_id=node.id)
        records: list[dict[str, Any]] = []

        for doc in docs:
            if not await ctx.checkpoint():
                break

            chunks = split_into_chunks(doc.get("text", ""))
            for chunk in chunks:
                if not await ctx.checkpoint():
                    break

                if ctx.engine_mode == "demo" and getattr(ctx, "fixture_records", None):
                    candidates = []
                    for fr in ctx.fixture_records:
                        raw_data = fr.get("data", {})
                        evidence = {}
                        for fname, val in raw_data.items():
                            evidence[fname] = fr.get("source_snippet", str(val))
                        candidates.append({
                            "fields": raw_data,
                            "evidence": evidence,
                        })
                else:
                    candidates = await extract_from_chunk(chunk, ctx.spec.fields, ctx.llm)

                for cand in candidates:
                    verification = verify_candidate(
                        candidate=cand,
                        chunk_text=chunk.text,
                        chunk_start_offset=chunk.start_offset,
                        source_url=doc.get("url", ""),
                        field_specs=ctx.spec.fields,
                    )

                    if verification.verification_status != "rejected":
                        rec_id = str(uuid4())
                        rec_dict = {
                            "id": rec_id,
                            "data": verification.fields,
                            "source_url": doc.get("url", ""),
                            "source_snippet": chunk.text[:300],
                            "confidence": verification.confidence,
                            "verification_status": verification.verification_status,
                            "field_verifications": [
                                {
                                    "field_name": fv.field_name,
                                    "value": str(fv.extracted_value) if fv.extracted_value is not None else None,
                                    "evidence_text": fv.evidence_text,
                                    "evidence_start": fv.evidence_start,
                                    "evidence_end": fv.evidence_end,
                                    "source_url": fv.source_url,
                                    "confidence": fv.confidence,
                                    "verified": fv.verified,
                                }
                                for fv in verification.field_verifications
                            ],
                        }
                        records.append(rec_dict)
                        ctx.counters["records"] = ctx.counters.get("records", 0) + 1
                        ctx.emit_log("INFO", f"Extracted candidate: {list(verification.fields.values())[:1]} (conf: {verification.confidence:.0%})", node_id=node.id)

        ctx.emit_log("SUCCESS", f"Extraction completed: {len(records)} evidence-verified candidates", node_id=node.id)
        return NodeResult(
            status="succeeded",
            items_in=len(docs),
            items_out=len(records),
            data={"records": records},
        )


class NormalizeNode(BaseNode):
    node_type = "normalize"

    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        records = inputs.get("records", [])
        field_type_map = {f.name: f.type for f in ctx.spec.fields}

        for rec in records:
            data = rec.get("data", {})
            normalized_data = {}
            for k, v in data.items():
                ftype = field_type_map.get(k, "string")
                normalized_data[k] = apply_normalizers(v, ftype)
            rec["data"] = normalized_data

        return NodeResult(
            status="succeeded",
            items_in=len(records),
            items_out=len(records),
            data={"records": records},
        )


class ValidateNode(BaseNode):
    node_type = "validate"

    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        records = inputs.get("records", [])
        field_validators_map = {f.name: f.validators for f in ctx.spec.fields}

        for rec in records:
            data = rec.get("data", {})
            for k, v in list(data.items()):
                validators = field_validators_map.get(k, [])
                if validators and v is not None:
                    ok, fixed, _ = run_validators(v, validators)
                    if ok and fixed is not None:
                        data[k] = fixed
                    elif not ok:
                        data[k] = None  # discard invalid value

        return NodeResult(
            status="succeeded",
            items_in=len(records),
            items_out=len(records),
            data={"records": records},
        )


class DedupeNode(BaseNode):
    node_type = "dedupe"

    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        records = inputs.get("records", [])
        key_fields = [f.name for f in ctx.spec.fields if f.unique_key] or [ctx.spec.fields[0].name]

        dedup_res = deduplicate_records(records, key_fields)
        ctx.emit_log("SUCCESS", f"Deduplicated: {dedup_res.merged_count} duplicate records merged", node_id=node.id)

        return NodeResult(
            status="succeeded",
            items_in=len(records),
            items_out=len(dedup_res.records),
            data={"records": dedup_res.records, "merged_count": dedup_res.merged_count},
        )


class ScoreNode(BaseNode):
    node_type = "score"

    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        records = inputs.get("records", [])
        return NodeResult(
            status="succeeded",
            items_in=len(records),
            items_out=len(records),
            data={"records": records},
        )


class FinalizeNode(BaseNode):
    node_type = "finalize"

    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        records = inputs.get("records", [])
        ctx.emit_log("INFO", f"Saving {len(records)} records to database...", node_id=node.id)

        with Session(engine) as session:
            for rec in records:
                db_rec = ExtractedRecord(
                    id=rec.get("id") or str(uuid4()),
                    run_id=ctx.run_id,
                    data=json.dumps(rec.get("data", {})),
                    data_json=json.dumps(rec.get("data", {})),
                    source_url=rec.get("source_url", ""),
                    source_snippet=rec.get("source_snippet", ""),
                    confidence_score=rec.get("confidence", 0.0),
                    confidence=rec.get("confidence", 0.0),
                    verification_status=rec.get("verification_status", "verified"),
                    corroboration_count=rec.get("corroboration_count", 1),
                    sources_json=json.dumps(rec.get("sources", [])),
                    dedupe_key=rec.get("dedupe_key", ""),
                )
                session.add(db_rec)

                # Persist per-field provenance
                for fv in rec.get("field_verifications", []):
                    prov = FieldProvenance(
                        record_id=db_rec.id,
                        field_name=fv.get("field_name", ""),
                        value=fv.get("value"),
                        evidence_text=fv.get("evidence_text", ""),
                        evidence_start=fv.get("evidence_start", -1),
                        evidence_end=fv.get("evidence_end", -1),
                        source_url=fv.get("source_url", ""),
                        confidence=fv.get("confidence", 0.0),
                        verified=fv.get("verified", False),
                    )
                    session.add(prov)

            # Update run metrics
            avg_conf = sum(r.get("confidence", 0.0) for r in records) / len(records) if records else 0.0
            qr = quality_reporter.generate(
                run_id=ctx.run_id,
                records_in=len(records) + inputs.get("merged_count", 0),
                records_out=len(records),
                duplicates_merged=inputs.get("merged_count", 0),
                validation_failures={},
                rejection_reasons={},
                avg_confidence=avg_conf,
            )
            q_model = QualityReport(run_id=ctx.run_id, report_json=json.dumps(qr))
            session.add(q_model)

            # Update ExecutionRun
            run = session.get(ExecutionRun, ctx.run_id)
            if run:
                run.status = RunStatus.completed
                run.state = "completed"
                run.progress_pct = 100
                run.finished_at = datetime.now(timezone.utc)
                run.metrics_json = json.dumps(qr)
                session.add(run)

            session.commit()

        ctx.emit({"type": "done", "status": "completed", "run_id": ctx.run_id})
        ctx.emit_log("SUCCESS", f"Run complete: {len(records)} verified records saved.", node_id=node.id)

        return NodeResult(
            status="succeeded",
            items_in=len(records),
            items_out=len(records),
            data={"record_count": len(records)},
        )


class EnrichNode(BaseNode):
    node_type = "enrich"

    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        # Pass-through node for backward compatibility
        return NodeResult(status="succeeded", items_in=0, items_out=0, data=inputs)
