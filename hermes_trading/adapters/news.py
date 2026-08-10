import os
import time
import httpx
from . import require_schema

async def fetch(asset: str = "BTC/USDT") -> dict:
    key = os.getenv("NEWS_API_KEY", "")
    headlines = []
    source = "public-fallback"
    if key:
        query = asset.split("/")[0]
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://newsapi.org/v2/everything", params={"q": query, "pageSize": 5, "sortBy": "publishedAt", "apiKey": key})
            r.raise_for_status()
            headlines = [a.get("title", "") for a in r.json().get("articles", [])]
            source = "newsapi"
    return require_schema({"schema_version": "1.0", "source": source, "asset": asset, "timestamp": int(time.time()), "headlines": headlines})
