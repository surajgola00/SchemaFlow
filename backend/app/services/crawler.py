import asyncio
import httpx
from bs4 import BeautifulSoup
import html2text

async def check_robots_txt(url: str, use_mock: bool = True) -> bool:
    if use_mock:
        return True
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        async with httpx.AsyncClient() as client:
            resp = await client.get(robots_url, timeout=5.0)
            if resp.status_code == 200:
                return True
            return True
    except Exception:
        return True

async def fetch_page(url: str, use_mock: bool = True) -> str:
    if use_mock:
        return f"# Mock content for {url}\n\nThis is a mock page content."
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            h = html2text.HTML2Text()
            h.ignore_links = False
            return h.handle(str(soup))
    except Exception as e:
        return f"Failed to fetch {url}: {e}"
