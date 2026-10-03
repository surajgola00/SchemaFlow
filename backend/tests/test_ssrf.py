"""
Tests for SSRF prevention.
"""
import pytest
from app.services.crawler.ssrf import is_safe_url


class TestSSRF:
    def test_blocks_localhost(self):
        safe, reason = is_safe_url("http://localhost:8000/secret")
        assert safe is False
        assert "loopback" in reason.lower() or "blocked" in reason.lower()

    def test_blocks_loopback_ip(self):
        safe, reason = is_safe_url("http://127.0.0.1:8000")
        assert safe is False

    def test_blocks_aws_metadata(self):
        safe, reason = is_safe_url("http://169.254.169.254/latest/meta-data/")
        assert safe is False

    def test_blocks_file_scheme(self):
        safe, reason = is_safe_url("file:///etc/passwd")
        assert safe is False
        assert "scheme" in reason.lower()

    def test_allows_public_urls(self):
        safe, _ = is_safe_url("https://www.google.com")
        assert safe is True
