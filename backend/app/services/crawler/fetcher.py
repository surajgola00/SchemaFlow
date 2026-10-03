"""
Fetcher service — safe, compliant HTTP fetching with SSRF protection, robots.txt, rate limits, and HTML-to-text.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import bs4
import html2text
import httpx

from app.config import get_settings
from app.logging_config import get_logger
from app.services.crawler.rate_limiter import rate_limiter
from app.services.crawler.robots import robots_cache
from app.services.crawler.ssrf import is_safe_url

if TYPE_CHECKING:
    from app.services.executor.context import RunContext

log = get_logger(__name__)


class FetchResult:
    def __init__(
        self,
        url: str,
        title: str,
        text: str,
        http_status: int = 200,
        content_hash: str = "",
        blocked: bool = False,
        blocked_reason: str | None = None,
    ) -> None:
        self.url = url
        self.title = title
        self.text = text
        self.http_status = http_status
        self.content_hash = content_hash or hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        self.blocked = blocked
        self.blocked_reason = blocked_reason
        self.fetched_at = datetime.now(timezone.utc)


class Fetcher:
    ALLOWED_CONTENT_TYPES = frozenset([
        "text/html", "application/json", "application/xml",
        "text/plain", "text/xml", "application/atom+xml",
        "application/rss+xml",
    ])

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            settings = get_settings()
            self._client = httpx.AsyncClient(
                follow_redirects=False,
                timeout=httpx.Timeout(15.0),
                headers={"User-Agent": settings.user_agent},
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._client

    def _clean_html(self, html: str) -> str:
        soup = bs4.BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["nav", "footer", "script", "style", "header", "aside"]):
            tag.decompose()
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        cleaned = h.handle(str(soup))
        return cleaned[:8000]

    def _extract_title(self, html: str) -> str:
        soup = bs4.BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else ""

    async def fetch(self, url: str, ctx: Any = None) -> FetchResult | None:
        settings = get_settings()

        # 1. SSRF check
        safe, reason = is_safe_url(url)
        if not safe:
            if ctx:
                ctx.emit_log("WARNING", f"SSRF blocked: {url} — {reason}")
                ctx.emit({
                    "type": "compliance",
                    "run_id": ctx.run_id,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "data": {"event": "ssrf_blocked", "url": url, "reason": reason},
                })
            return None

        # 2. robots.txt
        allowed = await robots_cache.is_allowed(url, settings.user_agent)
        if ctx:
            ctx.emit({
                "type": "compliance",
                "run_id": ctx.run_id,
                "ts": datetime.now(timezone.utc).isoformat(),
                "data": {"event": "robots_check", "url": url, "allowed": allowed},
            })
        if not allowed:
            if ctx:
                ctx.emit_log("WARNING", f"robots.txt disallowed: {url}")
            return None

        # 3. Rate limiting
        domain = urlparse(url).netloc
        await rate_limiter.acquire(domain)

        # 4. Fetch loop handling redirects safely
        current_url = url
        hops = 0
        client = await self.get_client()

        try:
            while hops <= settings.max_redirects:
                resp = await client.get(current_url, follow_redirects=False)
                if ctx and hasattr(ctx, "counters"):
                    ctx.counters["pages"] = ctx.counters.get("pages", 0) + 1

                if resp.is_redirect:
                    next_url = resp.headers.get("location", "")
                    if not next_url:
                        break
                    # Re-check SSRF for redirection destination
                    safe, reason = is_safe_url(next_url)
                    if not safe:
                        if ctx:
                            ctx.emit_log("WARNING", f"SSRF blocked on redirect: {next_url}")
                        return None
                    current_url = next_url
                    hops += 1
                    continue

                if resp.status_code in (401, 403, 429):
                    if ctx:
                        ctx.emit_log("WARNING", f"Access blocked ({resp.status_code}): {current_url}")
                        ctx.emit({
                            "type": "compliance",
                            "run_id": ctx.run_id,
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "data": {"event": "source_blocked", "url": current_url, "status": resp.status_code},
                        })
                    return None

                if resp.status_code >= 400:
                    if ctx:
                        ctx.emit_log("WARNING", f"HTTP {resp.status_code} for {current_url}")
                    return None

                # Content-Type check
                ct = resp.headers.get("content-type", "").split(";")[0].strip()
                if not any(ct.startswith(act) for act in self.ALLOWED_CONTENT_TYPES):
                    if ctx:
                        ctx.emit_log("WARNING", f"Skipping non-text content-type {ct}: {current_url}")
                    return None

                # Size cap
                if len(resp.content) > settings.max_response_size_bytes:
                    if ctx:
                        ctx.emit_log("WARNING", f"Response too large ({len(resp.content)} bytes): {current_url}")
                    return None

                text = self._clean_html(resp.text)
                title = self._extract_title(resp.text) or current_url
                content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

                return FetchResult(
                    url=url,
                    title=title,
                    text=text,
                    http_status=resp.status_code,
                    content_hash=content_hash,
                )

            if ctx:
                ctx.emit_log("WARNING", f"Exceeded max redirects for {url}")
            return None

        except httpx.TimeoutException:
            if ctx:
                ctx.emit_log("WARNING", f"Timeout fetching {url}")
            return None
        except Exception as e:
            if ctx:
                ctx.emit_log("ERROR", f"Error fetching {url}: {e}")
            return None


fetcher = Fetcher()
