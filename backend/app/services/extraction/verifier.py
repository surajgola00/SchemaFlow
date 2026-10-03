"""
Evidence Verifier — checks quotes against source chunks and ensures extracted values are factually grounded.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Optional

from rapidfuzz import fuzz

from app.schemas.workflow import FieldSpec


@dataclass
class FieldVerification:
    field_name: str
    extracted_value: Optional[Any]
    evidence_text: str
    evidence_start: int
    evidence_end: int
    source_url: str
    confidence: float
    verified: bool
    rejection_reason: Optional[str] = None


@dataclass
class RecordVerification:
    fields: dict[str, Any]
    field_verifications: list[FieldVerification]
    confidence: float
    verification_status: str  # "verified" | "partial" | "rejected"
    rejection_reason: Optional[str] = None


def _normalize_text(text: str) -> str:
    """Normalize unicode, collapse whitespace, lowercase."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def verify_candidate(
    candidate: dict[str, Any],
    chunk_text: str,
    chunk_start_offset: int,
    source_url: str,
    field_specs: list[FieldSpec],
) -> RecordVerification:
    """
    Verify extracted candidate against chunk evidence.
    1. Check evidence quote is actually present in chunk_text (exact or fuzzy >= 90%).
    2. Check that the extracted value is grounded in the quote (containment, numbers, or fuzzy >= 85%).
    3. Nullify ungrounded optional fields; reject entire record if required fields fail.
    4. Compute weighted confidence (2x weight for required fields).
    """
    fields_dict = candidate.get("fields", {})
    evidence_dict = candidate.get("evidence", {})
    field_specs_map = {fs.name: fs for fs in field_specs}

    field_verifications: list[FieldVerification] = []
    final_fields: dict[str, Any] = {}
    has_required_failure = False
    required_failure_reasons: list[str] = []

    norm_chunk = _normalize_text(chunk_text)

    for field_name, raw_value in fields_dict.items():
        evidence_quote = str(evidence_dict.get(field_name, "") or "")
        fspec = field_specs_map.get(field_name)

        ev_start = -1
        ev_end = -1
        match_quality = 0.0

        if evidence_quote.strip():
            norm_evidence = _normalize_text(evidence_quote)

            # Exact match check
            pos = norm_chunk.find(norm_evidence)
            if pos >= 0:
                ev_start = chunk_start_offset + pos
                ev_end = ev_start + len(evidence_quote)
                match_quality = 1.0
            else:
                # Fuzzy partial ratio or token_set_ratio (for quotes with ellipses like 'founded... in Bengaluru')
                clean_ev = re.sub(r"\.{2,}", " ", norm_evidence)
                clean_ev = re.sub(r"\s+", " ", clean_ev).strip()
                p_ratio = fuzz.partial_ratio(clean_ev, norm_chunk) / 100.0
                ts_ratio = fuzz.token_set_ratio(clean_ev, norm_chunk) / 100.0
                best_ratio = max(p_ratio, ts_ratio)

                if best_ratio >= 0.80:
                    match_quality = best_ratio
                    ev_start = chunk_start_offset
                    ev_end = chunk_start_offset + len(chunk_text)

        evidence_found = ev_start >= 0

        # Step 2: Check value is supported by evidence
        value_supported = False
        if evidence_found and raw_value is not None:
            str_val = str(raw_value)
            norm_val = _normalize_text(str_val)
            norm_ev = _normalize_text(evidence_quote)

            if norm_val and (norm_val in norm_ev or norm_ev in norm_val):
                value_supported = True
            elif norm_val and fuzz.partial_ratio(norm_val, norm_ev) >= 85:
                value_supported = True
            else:
                # Numeric equality check
                try:
                    num_val_matches = re.findall(r"\d+\.?\d*", norm_val)
                    num_ev_matches = re.findall(r"\d+\.?\d*", norm_ev)
                    if num_val_matches and any(float(n1) == float(n2) for n1 in num_val_matches for n2 in num_ev_matches):
                        value_supported = True
                except (ValueError, TypeError):
                    pass

        # Step 3: Compute field confidence
        if evidence_found and value_supported:
            field_confidence = max(0.85, match_quality * 0.9 + 0.1)
        elif evidence_found and not value_supported:
            field_confidence = 0.3
        else:
            field_confidence = 0.0

        verified = evidence_found and value_supported
        rejection_reason = None
        accepted_value = None

        if verified:
            accepted_value = raw_value
        else:
            rejection_reason = "evidence_not_found" if not evidence_found else "value_not_in_evidence"
            if fspec and fspec.required:
                has_required_failure = True
                required_failure_reasons.append(f"{field_name}: {rejection_reason}")

        final_fields[field_name] = accepted_value
        field_verifications.append(
            FieldVerification(
                field_name=field_name,
                extracted_value=accepted_value,
                evidence_text=evidence_quote,
                evidence_start=ev_start,
                evidence_end=ev_end,
                source_url=source_url,
                confidence=round(field_confidence, 3),
                verified=verified,
                rejection_reason=rejection_reason,
            )
        )

    # Check for any required fields missing from fields_dict entirely
    for fs in field_specs:
        if fs.required and fs.name not in fields_dict:
            has_required_failure = True
            required_failure_reasons.append(f"{fs.name}: missing_required_field")
            final_fields[fs.name] = None
            field_verifications.append(
                FieldVerification(
                    field_name=fs.name,
                    extracted_value=None,
                    evidence_text="",
                    evidence_start=-1,
                    evidence_end=-1,
                    source_url=source_url,
                    confidence=0.0,
                    verified=False,
                    rejection_reason="missing_required_field",
                )
            )

    # Record-level confidence: weighted average
    if field_verifications:
        total_weight = 0.0
        weighted_sum = 0.0
        for fv in field_verifications:
            fspec = field_specs_map.get(fv.field_name)
            weight = 2.0 if (fspec and fspec.required) else 1.0
            weighted_sum += fv.confidence * weight
            total_weight += weight
        record_confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
    else:
        record_confidence = 0.0

    if has_required_failure:
        verification_status = "rejected"
    elif all(fv.verified for fv in field_verifications if fv.extracted_value is not None):
        verification_status = "verified"
    else:
        verification_status = "partial"

    return RecordVerification(
        fields=final_fields,
        field_verifications=field_verifications,
        confidence=round(record_confidence, 3),
        verification_status=verification_status,
        rejection_reason="; ".join(required_failure_reasons) if required_failure_reasons else None,
    )
