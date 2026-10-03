"""
Tests for Fetcher service using respx:
1. robots.txt disallow rules are respected
2. Per-domain rate limit is enforced
3. SSRF redirect-to-private IP/host is blocked
4. Response size cap is enforced
5. 401, 403, 429 responses are marked blocked, never bypassed
"""
import asyncio
import time
import pytest
import respx
import httpx

from app.config import get_settings
from app.services.crawler.fetcher import fetcher
from app.services.crawler.robots import robots_cache
from app.services.crawler.rate_limiter import rate_limiter


class MockRunContext:
    def __init__(self):
        self.run_id = "test_fetch_run"
        self.counters = {"pages": 0}
        self.logs = []
        self.events = []

    async def checkpoint(self) -> bool:
        return True

    def emit_log(self, level: str, message: str, node_id: str = ""):
        self.logs.append((level, message))

    def emit(self, event: dict):
        self.events.append(event)


@pytest.fixture(autouse=True)
def mock_dns():
    import socket
    from unittest.mock import patch

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if host in ("localhost", "127.0.0.1", "169.254.169.254"):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, port or 80))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.215.14", port or 80))]

    with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
        yield


@pytest.fixture(autouse=True)
async def reset_fetcher():
    if fetcher._client is not None and not fetcher._client.is_closed:
        await fetcher._client.aclose()
    fetcher._client = None
    robots_cache.clear()
    yield
    if fetcher._client is not None and not fetcher._client.is_closed:
        await fetcher._client.aclose()
    fetcher._client = None


@pytest.mark.asyncio
@respx.mock
async def test_robots_disallow_respected():
    """Verify that robots.txt disallow rules are strictly respected."""
    robots_cache.clear()
    user_agent = get_settings().user_agent

    # Mock robots.txt with Disallow: /secret/
    respx.get("http://compliance-test.com/robots.txt").mock(
        return_value=httpx.Response(
            200,
            text=f"User-agent: *\nDisallow: /secret/\nAllow: /public/\n",
        )
    )
    # Mock allowed page
    respx.get("http://compliance-test.com/public/data").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            text="<html><head><title>Public</title></head><body><h1>Allowed Content</h1></body></html>",
        )
    )

    ctx = MockRunContext()

    # 1. Fetch disallowed URL -> must return None
    result_blocked = await fetcher.fetch("http://compliance-test.com/secret/private-data", ctx)
    assert result_blocked is None
    # Verify compliance event emitted
    compliance_events = [e for e in ctx.events if e.get("type") == "compliance"]
    assert any(e["data"].get("event") == "robots_check" and not e["data"].get("allowed") for e in compliance_events)

    # 2. Fetch allowed URL -> must succeed
    result_allowed = await fetcher.fetch("http://compliance-test.com/public/data", ctx)
    assert result_allowed is not None
    assert "Allowed Content" in result_allowed.text
    assert result_allowed.title == "Public"


@pytest.mark.asyncio
async def test_per_domain_rate_limit():
    """Verify per-domain rate limiter delays requests to same domain."""
    domain = "ratelimit-domain.com"
    # Acquire token once
    await rate_limiter.acquire(domain)

    # Immediate second acquire must measure interval
    t0 = time.monotonic()
    await rate_limiter.acquire(domain)
    duration = time.monotonic() - t0

    # Minimum interval at 1.0 rps is approx 0.8-1.1s
    # Even with small timing variations, it should have caused a measurable delay
    assert duration >= 0.5


@pytest.mark.asyncio
@respx.mock
async def test_ssrf_redirect_to_private_blocked():
    """Verify SSRF protection catches redirects to localhost, 127.0.0.1, or cloud metadata."""
    robots_cache.clear()

    # Allow robots.txt
    respx.get("http://redirect-ssrf.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
    )

    # Initial public URL redirects to AWS metadata private IP (169.254.169.254)
    respx.get("http://redirect-ssrf.com/hop").mock(
        return_value=httpx.Response(
            302,
            headers={"Location": "http://169.254.169.254/latest/meta-data/"},
        )
    )

    ctx = MockRunContext()
    res = await fetcher.fetch("http://redirect-ssrf.com/hop", ctx)

    # Must be blocked and return None
    assert res is None
    # Check log
    assert any("SSRF blocked on redirect" in msg for _, msg in ctx.logs)


@pytest.mark.asyncio
@respx.mock
async def test_response_size_cap():
    """Verify fetcher rejects documents exceeding max_response_size_bytes."""
    robots_cache.clear()
    settings = get_settings()

    respx.get("http://large-document.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
    )

    # Create oversized content
    oversized_text = "x" * (settings.max_response_size_bytes + 2048)
    respx.get("http://large-document.com/oversized").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            text=f"<html><body>{oversized_text}</body></html>",
        )
    )

    ctx = MockRunContext()
    res = await fetcher.fetch("http://large-document.com/oversized", ctx)

    assert res is None
    assert any("Response too large" in msg for _, msg in ctx.logs)


@pytest.mark.asyncio
@respx.mock
async def test_login_wall_and_rate_limit_marked_blocked():
    """Verify HTTP 401, 403, and 429 are marked blocked and never bypassed."""
    robots_cache.clear()

    respx.get("http://login-walled.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
    )

    for status_code in (401, 403, 429):
        url = f"http://login-walled.com/status-{status_code}"
        respx.get(url).mock(
            return_value=httpx.Response(status_code, text="Access Denied / Login required")
        )

        ctx = MockRunContext()
        res = await fetcher.fetch(url, ctx)

        assert res is None
        # Verify blocked event was emitted in compliance
        source_blocked_events = [
            e for e in ctx.events
            if e.get("type") == "compliance" and e.get("data", {}).get("event") == "source_blocked"
        ]
        assert len(source_blocked_events) > 0
        assert source_blocked_events[0]["data"]["status"] == status_code
        assert any(f"Access blocked ({status_code})" in msg for _, msg in ctx.logs)
