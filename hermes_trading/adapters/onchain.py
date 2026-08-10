import os
import time
import httpx
from . import require_schema

async def fetch(asset: str = "BTC/USDT") -> dict:
    key = os.getenv("GLASSNODE_API_KEY", "")
    payload = {"schema_version": "1.0", "source": "public-fallback", "asset": asset, "timestamp": int(time.time()), "active_addresses": None, "note": "set GLASSNODE_API_KEY for premium on-chain data"}
    if key and asset.upper().startswith("BTC"):
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://api.glassnode.com/v1/metrics/addresses/active_count", params={"a": "BTC", "api_key": key})
            r.raise_for_status()
            data = r.json()
            payload.update({"source": "glassnode", "active_addresses": data[-1].get("v") if data else None})
    return require_schema(payload)
