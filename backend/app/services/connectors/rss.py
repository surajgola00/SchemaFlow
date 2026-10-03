"""
RSS / Atom feed connector using feedparser.
"""
from __future__ import annotations

from typing import Any
import feedparser
import httpx

from app.services.connectors.base import Connector


class RSSConnector(Connector):
    name = "rss"

    async def discover(self, spec: Any, ctx: Any) -> list[str]:
        seed_urls = spec.source_strategy.seed_urls
        urls: list[str] = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in seed_urls:
                if ctx and not await ctx.checkpoint():
                    break
                try:
                    res = await client.get(url)
                    feed = feedparser.parse(res.text)
                    for entry in feed.entries[:15]:
                        link = getattr(entry, "link", None)
                        if link and link.startswith("http") and link not in urls:
                            urls.append(link)
                except Exception:
                    continue

        return urls
