"""
Tests for normalizers: URL canonicalization, currency parsing, date parsing, whitespace.
"""
import pytest
from app.services.quality.normalizers import (
    normalize_url,
    normalize_whitespace,
    parse_currency,
    normalize_date,
    apply_normalizers,
)


class TestNormalizers:
    def test_normalize_whitespace(self):
        assert normalize_whitespace("  hello   world \n \t ") == "hello world"
        assert normalize_whitespace("") == ""

    def test_normalize_url(self):
        # Strips tracking params
        dirty = "https://WWW.Example.com/jobs/?utm_source=twitter&utm_medium=cpc&ref=xyz"
        clean = normalize_url(dirty)
        assert "utm_source" not in clean
        assert "ref" not in clean
        assert clean.startswith("https://example.com/jobs")

    def test_parse_currency_indian_units(self):
        amt, code = parse_currency("₹41 Cr")
        assert amt == 410000000.0
        assert code == "INR"

        amt, code = parse_currency("Rs 50 Lakh")
        assert amt == 5000000.0
        assert code == "INR"

    def test_parse_currency_global_units(self):
        amt, code = parse_currency("$2.5M")
        assert amt == 2500000.0
        assert code == "USD"

        amt, code = parse_currency("€500K")
        assert amt == 500000.0
        assert code == "EUR"

        amt, code = parse_currency("$1.2B")
        assert amt == 1200000000.0
        assert code == "USD"

    def test_normalize_date(self):
        assert normalize_date("2026-03-15") == "2026-03-15"
        assert normalize_date("March 15, 2026") == "2026-03-15"
        # Range format
        assert normalize_date("March 15-17, 2026") == "2026-03-15"

    def test_apply_normalizers(self):
        url_res = apply_normalizers("example.com/careers/?utm_source=ad", "url")
        assert "utm_source" not in str(url_res)
        assert str(url_res).startswith("https://")
