import time
import httpx
from . import require_schema

async def fetch(asset: str = "BTC/USDT") -> dict:
    # Free public proxy for broad market risk appetite: SPY latest daily close via Stooq CSV.
    risk_proxy = None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://stooq.com/q/l/?s=spy.us&i=d")
            r.raise_for_status()
            lines = [line for line in r.text.splitlines() if line and not line.startswith("Symbol")]
            if lines:
                risk_proxy = float(lines[-1].split(",")[6])
    except Exception:
        risk_proxy = None
    return require_schema({"schema_version": "1.0", "source": "stooq", "asset": asset, "timestamp": int(time.time()), "risk_proxy_spy_close": risk_proxy})
