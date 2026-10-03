"""
Quality Reporter — generates actionable run summary reports.
"""
from __future__ import annotations

from typing import Any


class QualityReporter:
    def generate(
        self,
        run_id: str,
        records_in: int,
        records_out: int,
        duplicates_merged: int,
        validation_failures: dict[str, int],
        rejection_reasons: dict[str, int],
        fields_fixed_examples: list[dict[str, str]] | None = None,
        avg_confidence: float = 0.0,
    ) -> dict[str, Any]:
        verified_ratio = (records_out / records_in) if records_in > 0 else 1.0

        return {
            "run_id": run_id,
            "rows_in": records_in,
            "rows_out": records_out,
            "duplicates_merged": duplicates_merged,
            "verified_ratio": round(verified_ratio, 3),
            "avg_confidence": round(avg_confidence, 3),
            "validation_failures_by_reason": validation_failures or {},
            "rejection_reasons_by_reason": rejection_reasons or {},
            "fields_fixed_examples": fields_fixed_examples or [],
        }


quality_reporter = QualityReporter()
