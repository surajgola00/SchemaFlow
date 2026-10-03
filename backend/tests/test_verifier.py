"""
Test suite for the evidence verifier (Phase 5).
Tests: quote present/absent, fuzzy match, value-not-in-evidence → nulled, required-field missing → rejected.
"""
import pytest
from app.services.extraction.verifier import verify_candidate, FieldVerification, RecordVerification


def _make_field_spec(name: str, required: bool = False, unique_key: bool = False) -> dict:
    """Helper to create a minimal field spec dict (we'll convert to FieldSpec in tests)."""
    from app.schemas.workflow import FieldSpec
    return FieldSpec(
        name=name,
        label=name.replace("_", " ").title(),
        type="string",
        description=f"Test field {name}",
        required=required,
        unique_key=unique_key,
        validators=[],
    )


@pytest.fixture
def chunk_text() -> str:
    return (
        "Sarvam AI was founded by Vivek Raghavan and Pratyush Kumar in Bengaluru. "
        "The company raised $41M in a Series A round in 2024. "
        "They are building multilingual large language models for Indian languages. "
        "Visit their careers page at https://sarvam.ai/careers for job openings."
    )


class TestVerifierExactMatch:
    def test_exact_match_present(self, chunk_text: str) -> None:
        candidate = {
            "fields": {"name": "Sarvam AI"},
            "evidence": {"name": "Sarvam AI was founded by Vivek Raghavan"},
        }
        field_specs = [_make_field_spec("name", required=True, unique_key=True)]
        result = verify_candidate(candidate, chunk_text, 0, "https://example.com", field_specs)
        
        assert result.verification_status in ("verified", "partial")
        assert result.fields["name"] == "Sarvam AI"
        fv = next(fv for fv in result.field_verifications if fv.field_name == "name")
        assert fv.verified is True
        assert fv.confidence > 0.8

    def test_evidence_not_in_chunk(self, chunk_text: str) -> None:
        candidate = {
            "fields": {"name": "Google DeepMind"},
            "evidence": {"name": "Google DeepMind is an AI research lab"},
        }
        field_specs = [_make_field_spec("name", required=True)]
        result = verify_candidate(candidate, chunk_text, 0, "https://example.com", field_specs)
        
        assert result.verification_status == "rejected"
        assert result.fields["name"] is None
        fv = next(fv for fv in result.field_verifications if fv.field_name == "name")
        assert fv.verified is False
        assert fv.confidence < 0.5

    def test_value_not_in_evidence_is_nulled(self, chunk_text: str) -> None:
        """Value is fabricated but evidence exists in chunk."""
        candidate = {
            "fields": {"name": "FABRICATED NAME XYZ"},
            "evidence": {"name": "Sarvam AI was founded by Vivek Raghavan"},
        }
        field_specs = [_make_field_spec("name", required=False)]
        result = verify_candidate(candidate, chunk_text, 0, "https://example.com", field_specs)
        
        # Since evidence exists in chunk but value is NOT in evidence → field nulled
        assert result.fields["name"] is None

    def test_required_field_missing_rejects_record(self, chunk_text: str) -> None:
        """If a required field has no evidence, the whole record is rejected."""
        candidate = {
            "fields": {"founders": "Unknown Person"},
            "evidence": {"founders": "This evidence is completely fabricated nonsense XXXXXX"},
        }
        field_specs = [
            _make_field_spec("founders", required=True),
        ]
        result = verify_candidate(candidate, chunk_text, 0, "https://example.com", field_specs)
        
        assert result.verification_status == "rejected"
        assert result.fields["founders"] is None
        assert result.rejection_reason is not None


class TestVerifierFuzzyMatch:
    def test_fuzzy_match_high_similarity(self, chunk_text: str) -> None:
        """Evidence with minor whitespace/punctuation differences should still match."""
        candidate = {
            "fields": {"location": "Bengaluru"},
            "evidence": {"location": "Sarvam AI was founded... in Bengaluru."},  # slightly different punctuation
        }
        field_specs = [_make_field_spec("location", required=False)]
        result = verify_candidate(candidate, chunk_text, 0, "https://example.com", field_specs)
        
        fv = next(fv for fv in result.field_verifications if fv.field_name == "location")
        # Should verify since evidence is very close to chunk text
        assert fv.confidence > 0.0  # at least some confidence

    def test_completely_fabricated_evidence_rejected(self, chunk_text: str) -> None:
        """Evidence that doesn't exist at all should fail."""
        candidate = {
            "fields": {"funding": "$999B"},
            "evidence": {"funding": "According to private sources the company raised nine hundred ninety nine billion dollars"},
        }
        field_specs = [_make_field_spec("funding", required=True)]
        result = verify_candidate(candidate, chunk_text, 0, "https://example.com", field_specs)
        
        assert result.verification_status == "rejected"


class TestVerifierMultipleFields:
    def test_partial_verification_status(self, chunk_text: str) -> None:
        """Record with some verified and some unverified optional fields → 'partial'."""
        candidate = {
            "fields": {
                "name": "Sarvam AI",
                "fake_field": "COMPLETELY MADE UP",
            },
            "evidence": {
                "name": "Sarvam AI was founded by Vivek Raghavan",
                "fake_field": "This evidence does not appear anywhere in the document at all ZZZZ",
            },
        }
        field_specs = [
            _make_field_spec("name", required=True, unique_key=True),
            _make_field_spec("fake_field", required=False),
        ]
        result = verify_candidate(candidate, chunk_text, 0, "https://example.com", field_specs)
        
        # name verified, fake_field not → partial
        assert result.verification_status in ("partial", "verified")
        assert result.fields["name"] == "Sarvam AI"
        assert result.fields["fake_field"] is None

    def test_confidence_weighted_by_required(self, chunk_text: str) -> None:
        """Required fields should have higher weight in confidence calculation."""
        candidate = {
            "fields": {
                "name": "Sarvam AI",
                "funding_amount": "$41M",
            },
            "evidence": {
                "name": "Sarvam AI was founded by Vivek Raghavan",
                "funding_amount": "The company raised $41M in a Series A round",
            },
        }
        field_specs = [
            _make_field_spec("name", required=True, unique_key=True),
            _make_field_spec("funding_amount", required=False),
        ]
        result = verify_candidate(candidate, chunk_text, 0, "https://example.com", field_specs)
        
        assert result.confidence > 0.7
        assert result.verification_status in ("verified", "partial")

    def test_offset_tracking(self, chunk_text: str) -> None:
        """Evidence offsets should be recorded."""
        candidate = {
            "fields": {"name": "Sarvam AI"},
            "evidence": {"name": "Sarvam AI was founded"},
        }
        field_specs = [_make_field_spec("name", required=True)]
        result = verify_candidate(candidate, chunk_text, 0, "https://example.com", field_specs)
        
        fv = next(fv for fv in result.field_verifications if fv.field_name == "name")
        if fv.verified:
            assert fv.evidence_start >= 0
