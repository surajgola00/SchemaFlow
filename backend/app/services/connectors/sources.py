"""
HackerNews, GitHub, Wikipedia, arXiv, Direct URLs, and Sitemap connectors.
"""
from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote, urlparse
import httpx

from app.services.connectors.base import Connector


class HackerNewsConnector(Connector):
    name = "hackernews"

    async def discover(self, spec: Any, ctx: Any) -> list[str]:
        queries = spec.source_strategy.seed_queries[:3]
        urls: list[str] = []

        async with httpx.AsyncClient(timeout=8.0) as client:
            for q in queries:
                try:
                    res = await client.get(
                        f"https://hn.algolia.com/api/v1/search?query={quote(q)}&tags=story&hitsPerPage=10"
                    )
                    data = res.json()
                    for hit in data.get("hits", []):
                        url = hit.get("url")
                        if url and url.startswith("http") and url not in urls:
                            urls.append(url)
                except Exception:
                    continue

        return urls


class GitHubConnector(Connector):
    name = "github"

    async def discover(self, spec: Any, ctx: Any) -> list[str]:
        queries = spec.source_strategy.seed_queries[:2]
        urls: list[str] = []

        async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": "SchemaFlow/2.0"}) as client:
            for q in queries:
                try:
                    res = await client.get(
                        f"https://api.github.com/search/repositories?q={quote(q)}&sort=stars&per_page=10"
                    )
                    data = res.json()
                    for item in data.get("items", []):
                        url = item.get("html_url")
                        if url and url not in urls:
                            urls.append(url)
                    await asyncio.sleep(1.0)  # GitHub unauthenticated rate protection
                except Exception:
                    continue

        return urls


class WikipediaConnector(Connector):
    name = "wikipedia"

    async def discover(self, spec: Any, ctx: Any) -> list[str]:
        queries = spec.source_strategy.seed_queries[:3]
        urls: list[str] = []

        async with httpx.AsyncClient(timeout=8.0) as client:
            for q in queries:
                try:
                    res = await client.get(
                        f"https://en.wikipedia.org/w/api.php?action=opensearch&search={quote(q)}&limit=5&format=json"
                    )
                    data = res.json()
                    if len(data) >= 4 and isinstance(data[3], list):
                        for url in data[3]:
                            if url and url not in urls:
                                urls.append(url)
                except Exception:
                    continue

        return urls


class ArxivConnector(Connector):
    name = "arxiv"

    async def discover(self, spec: Any, ctx: Any) -> list[str]:
        queries = spec.source_strategy.seed_queries[:2]
        urls: list[str] = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for q in queries:
                try:
                    res = await client.get(
                        f"http://export.arxiv.org/api/query?search_query=all:{quote(q)}&max_results=8&sortBy=submittedDate"
                    )
                    root = ET.fromstring(res.text)
                    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                        id_elem = entry.find("{http://www.w3.org/2005/Atom}id")
                        if id_elem is not None and id_elem.text:
                            url = id_elem.text.strip().replace("http://", "https://")
                            if url not in urls:
                                urls.append(url)
                except Exception:
                    continue

        return urls


class DirectURLsConnector(Connector):
    name = "direct_urls"

    async def discover(self, spec: Any, ctx: Any) -> list[str]:
        return list(spec.source_strategy.seed_urls)


class SitemapConnector(Connector):
    name = "sitemap"

    async def discover(self, spec: Any, ctx: Any) -> list[str]:
        domains = spec.source_strategy.domain_allowlist
        urls: list[str] = []

        async with httpx.AsyncClient(timeout=8.0) as client:
            for domain in domains:
                sitemap_url = f"https://{domain}/sitemap.xml"
                try:
                    res = await client.get(sitemap_url)
                    root = ET.fromstring(res.text)
                    for loc in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                        if loc.text and loc.text.startswith("http") and loc.text not in urls:
                            urls.append(loc.text.strip())
                            if len(urls) >= 30:
                                break
                except Exception:
                    continue

        return urls
