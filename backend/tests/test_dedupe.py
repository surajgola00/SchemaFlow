"""
Tests for 3-tier deduplication.
"""
import pytest
from app.services.quality.dedupe import deduplicate_records, build_dedupe_key


class TestDedupe:
    def test_build_dedupe_key(self):
        rec = {"name": "Sarvam AI", "location": "Bengaluru"}
        key = build_dedupe_key(rec, ["name"])
        assert key == "sarvam ai"

    def test_exact_key_dedupe(self):
        records = [
            {
                "data": {"name": "Sarvam AI", "funding": "$41M"},
                "source_url": "https://source1.com",
                "confidence": 0.90,
            },
            {
                "data": {"name": "Sarvam AI", "funding": "$41M Series A"},
                "source_url": "https://source2.com",
                "confidence": 0.95,
            },
        ]
        result = deduplicate_records(records, ["name"])
        assert len(result.records) == 1
        assert result.merged_count == 1
        # Higher confidence value preserved
        assert result.records[0]["data"]["funding"] == "$41M Series A"
        assert result.records[0]["corroboration_count"] == 2

    def test_canonical_url_dedupe(self):
        records = [
            {
                "data": {"name": "Startup Alpha"},
                "source_url": "https://example.com/company/alpha/?utm_source=twitter",
                "confidence": 0.85,
            },
            {
                "data": {"name": "Alpha Corp"},
                "source_url": "https://example.com/company/alpha",
                "confidence": 0.88,
            },
        ]
        result = deduplicate_records(records, ["name"])
        assert len(result.records) == 1
        assert result.merged_count == 1

    def test_fuzzy_dedupe(self):
        records = [
            {
                "data": {"name": "Krutrim SI Designs Private Limited"},
                "source_url": "https://source1.com",
                "confidence": 0.90,
            },
            {
                "data": {"name": "Krutrim SI Designs"},
                "source_url": "https://source2.com",
                "confidence": 0.92,
            },
        ]
        result = deduplicate_records(records, ["name"], fuzzy_threshold=0.85)
        assert len(result.records) == 1
        assert result.merged_count == 1
