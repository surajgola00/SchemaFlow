"""
Tests for field validators.
"""
import pytest
from app.services.quality.validators import (
    validate_url,
    validate_email,
    validate_phone,
    validate_regex,
    validate_min_len,
    validate_range,
    validate_enum,
    run_validators,
)


class TestValidators:
    def test_validate_url(self):
        ok, val, _ = validate_url("https://sarvam.ai")
        assert ok is True
        assert val == "https://sarvam.ai"

        ok, _, reason = validate_url("not a url at all")
        assert ok is False
        assert reason is not None

    def test_validate_email(self):
        ok, val, _ = validate_email("FOUNDER@SARVAM.AI")
        assert ok is True
        assert val == "founder@sarvam.ai"

        ok, _, reason = validate_email("invalid-email")
        assert ok is False

    def test_validate_min_len(self):
        ok, _, _ = validate_min_len("Sarvam AI", 3)
        assert ok is True

        ok, _, reason = validate_min_len("AI", 3)
        assert ok is False

    def test_validate_range(self):
        ok, _, _ = validate_range("50", 1, 100)
        assert ok is True

        ok, _, _ = validate_range("150", 1, 100)
        assert ok is False

    def test_validate_enum(self):
        ok, val, _ = validate_enum("seed", ["Pre-Seed", "Seed", "Series A"])
        assert ok is True
        assert val == "Seed"

        ok, _, _ = validate_enum("Series D", ["Seed", "Series A"])
        assert ok is False

    def test_run_validators_chain(self):
        specs = ["min_len:3", "regex:^[A-Z]"]
        ok, val, _ = run_validators("Valid String", specs)
        assert ok is True

        ok, _, reason = run_validators("lowercase string", specs)
        assert ok is False
        assert reason is not None
