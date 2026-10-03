"""
3-level Deduplication — Exact key match -> Canonical URL match -> Fuzzy token_set_ratio.
Merges records, retaining higher-confidence values and aggregating source provenance.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from rapidfuzz import fuzz

from app.services.quality.normalizers import normalize_url


@dataclass
class DedupeResult:
    records: list[dict[str, Any]]
    merged_count: int
    duplicate_groups: list[list[str]] = field(default_factory=list)


def build_dedupe_key(record_data: dict[str, Any], key_fields: list[str]) -> str:
    """Build a composite deduplication key from unique_key fields."""
    parts = []
    for f in key_fields:
        val = record_data.get(f, "")
        if val is not None:
            parts.append(str(val).strip().lower())
    return "|".join(parts)


def _merge_records(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge incoming into base, preserving higher confidence field values and appending sources."""
    merged = dict(base)
    base_data = dict(merged.get("data", {}))
    inc_data = incoming.get("data", {})

    base_conf = merged.get("confidence", 0.0)
    inc_conf = incoming.get("confidence", 0.0)

    # Merge fields: prefer non-null, or higher confidence if both present
    for k, v in inc_data.items():
        if k not in base_data or base_data[k] is None:
            base_data[k] = v
        elif inc_conf > base_conf and v is not None:
            base_data[k] = v

    merged["data"] = base_data

    # Corroboration count
    merged["corroboration_count"] = merged.get("corroboration_count", 1) + incoming.get("corroboration_count", 1)
    merged["confidence"] = max(base_conf, inc_conf)

    # Aggregate sources
    base_sources = merged.get("sources", [])
    if isinstance(base_sources, str):
        try:
            base_sources = json.loads(base_sources)
        except Exception:
            base_sources = []

    inc_sources = incoming.get("sources", [])
    if isinstance(inc_sources, str):
        try:
            inc_sources = json.loads(inc_sources)
        except Exception:
            inc_sources = []

    all_sources = list(base_sources)
    if incoming.get("source_url") and not any(s.get("url") == incoming["source_url"] for s in all_sources if isinstance(s, dict)):
        all_sources.append({"url": incoming["source_url"], "connector": incoming.get("connector", "web")})
    for s in inc_sources:
        if s not in all_sources:
            all_sources.append(s)

    merged["sources"] = all_sources
    return merged


def deduplicate_records(
    records: list[dict[str, Any]],
    key_fields: list[str],
    fuzzy_threshold: float = 0.90,
) -> DedupeResult:
    """
    Deduplicate a list of records using 3 cascading tiers:
    1. Exact match on dedupe_key (built from unique_key fields)
    2. Exact match on normalized source_url
    3. Fuzzy token_set_ratio match (>= fuzzy_threshold) on key fields
    """
    if not records:
        return DedupeResult(records=[], merged_count=0)

    merged_count = 0
    duplicate_groups: list[list[str]] = []
    output_records: list[dict[str, Any]] = []

    for incoming in records:
        rec_data = incoming.get("data", {})
        d_key = incoming.get("dedupe_key") or build_dedupe_key(rec_data, key_fields)
        incoming["dedupe_key"] = d_key
        canonical_url = normalize_url(incoming.get("source_url", ""))

        matched_idx = -1

        # Check 1: Exact key match
        if d_key:
            for idx, existing in enumerate(output_records):
                if existing.get("dedupe_key") == d_key:
                    matched_idx = idx
                    break

        # Check 2: Canonical source URL match (if not matched yet and URL exists)
        if matched_idx == -1 and canonical_url:
            for idx, existing in enumerate(output_records):
                exist_url = normalize_url(existing.get("source_url", ""))
                if exist_url and exist_url == canonical_url:
                    matched_idx = idx
                    break

        # Check 3: Fuzzy token_set_ratio match on key fields
        if matched_idx == -1 and d_key:
            for idx, existing in enumerate(output_records):
                exist_key = existing.get("dedupe_key", "")
                if exist_key and d_key:
                    sim = fuzz.token_set_ratio(d_key, exist_key) / 100.0
                    if sim >= fuzzy_threshold:
                        matched_idx = idx
                        break

        if matched_idx >= 0:
            # Merge
            base = output_records[matched_idx]
            output_records[matched_idx] = _merge_records(base, incoming)
            merged_count += 1
            duplicate_groups.append([base.get("id", str(matched_idx)), incoming.get("id", "new")])
        else:
            # Add new
            new_rec = dict(incoming)
            if "corroboration_count" not in new_rec:
                new_rec["corroboration_count"] = 1
            if "sources" not in new_rec and new_rec.get("source_url"):
                new_rec["sources"] = [{"url": new_rec["source_url"], "connector": new_rec.get("connector", "web")}]
            output_records.append(new_rec)

    return DedupeResult(
        records=output_records,
        merged_count=merged_count,
        duplicate_groups=duplicate_groups,
    )
