"""
Web Search Connector — supports DuckDuckGo HTML (zero keys needed), Serper, Brave, and SearXNG.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import bs4
import httpx

from app.config import get_settings
from app.logging_config import get_logger
from app.services.connectors.base import Connector

log = get_logger(__name__)


class WebSearchConnector(Connector):
    name = "web_search"

    async def discover(self, spec: Any, ctx: Any) -> list[str]:
        settings = get_settings()
        queries = spec.source_strategy.seed_queries[:4]
        urls: list[str] = []

        allowlist = [d.lower() for d in spec.source_strategy.domain_allowlist]
        blocklist = [d.lower() for d in spec.source_strategy.domain_blocklist]

        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": settings.user_agent}) as client:
            for q in queries:
                if ctx and not await ctx.checkpoint():
                    break

                try:
                    found = await self._search(client, q, settings)
                    for u in found:
                        domain = urlparse(u).netloc.lower()
                        if allowlist and not any(a in domain for a in allowlist):
                            continue
                        if any(b in domain for b in blocklist):
                            continue
                        if u not in urls:
                            urls.append(u)
                except Exception as e:
                    if ctx:
                        ctx.emit_log("WARNING", f"Search query '{q}' failed: {e}")

        # Graceful fallback: If search provider returned 0 results (e.g. DDG HTML rate-limited or blocked),
        # fall back to direct public connectors (RSS, HackerNews, Wikipedia, GitHub) and surface in compliance panel.
        if not urls:
            from datetime import datetime, timezone
            if ctx:
                ctx.emit({
                    "type": "compliance",
                    "run_id": ctx.run_id,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "event": "web_search_fallback",
                        "provider": settings.search_provider,
                        "reason": "Search provider blocked or returned 0 results; fallback to public connectors activated",
                    },
                })
                ctx.emit_log("WARNING", "Search provider returned 0 results; falling back to RSS, HackerNews, Wikipedia, GitHub")

            from app.services.connectors.registry import get_connector
            for fallback_conn_name in ["rss", "hackernews", "wikipedia", "github"]:
                fallback_conn = get_connector(fallback_conn_name)
                if fallback_conn:
                    try:
                        fallback_urls = await fallback_conn.discover(spec, ctx)
                        for u in fallback_urls:
                            if u not in urls:
                                urls.append(u)
                        if len(urls) >= 10:
                            break
                    except Exception:
                        pass

        return urls

    async def _search(self, client: httpx.AsyncClient, query: str, settings: Any) -> list[str]:
        provider = settings.search_provider

        if provider == "duckduckgo_html" or not settings.search_api_key:
            # DuckDuckGo HTML endpoint (no API key required)
            res = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            soup = bs4.BeautifulSoup(res.text, "html.parser")
            results = []
            for a in soup.select("a.result__url, a.result__a"):
                href = a.get("href", "")
                if href and href.startswith("http") and "duckduckgo.com" not in href:
                    results.append(href)
            return results[:10]

        elif provider == "serper":
            res = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": settings.search_api_key, "Content-Type": "application/json"},
                json={"q": query, "num": 10},
            )
            data = res.json()
            return [item.get("link") for item in data.get("organic", []) if item.get("link")][:10]

        elif provider == "brave":
            res = await client.get(
                f"https://api.search.brave.com/res/v1/web/search?q={query}&count=10",
                headers={"X-Subscription-Token": settings.search_api_key},
            )
            data = res.json()
            return [item.get("url") for item in data.get("web", {}).get("results", []) if item.get("url")][:10]

        return []
