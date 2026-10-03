"""
robots.txt verification cache using urllib.robotparser.
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx

from app.logging_config import get_logger

log = get_logger(__name__)


class RobotsCache:
    def __init__(self) -> None:
        self._cache: dict[str, RobotFileParser] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, url: str, user_agent: str) -> bool:
        """Verify if robots.txt permits crawling the given url."""
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain:
            return False

        async with self._lock:
            if domain in self._cache:
                parser = self._cache[domain]
                return parser.can_fetch(user_agent, url)

        # Fetch robots.txt
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(robots_url, headers={"User-Agent": user_agent})
                if res.status_code == 200:
                    lines = res.text.splitlines()
                    parser.parse(lines)
                elif res.status_code in (401, 403):
                    # Deny all
                    parser.disallow_all = True  # type: ignore[attr-defined]
                else:
                    # Allow all (fail open on 404/500)
                    parser.allow_all = True  # type: ignore[attr-defined]
        except Exception as e:
            log.warning(f"Error fetching {robots_url}: {e}. Defaulting to allow.")
            parser.allow_all = True  # type: ignore[attr-defined]

        async with self._lock:
            self._cache[domain] = parser

        return parser.can_fetch(user_agent, url)

    def clear(self) -> None:
        self._cache.clear()


robots_cache = RobotsCache()
