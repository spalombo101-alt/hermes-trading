import asyncio
import json
import os
import time
from pathlib import Path
import yaml
from rich.console import Console
from .adapters import price

console = Console()

async def main():
    ROOT = Path("/app")
    STATE = ROOT / "state"
    
    console.log("[cyan]Booting hermes-trading worker for stocks in paper mode")
    
    failures = 0
    open_position = None
    
    while True:
        try:
            goal = yaml.safe_load((STATE / "goal.yaml").read_text())
            strategy = yaml.safe_load((STATE / "strategy.yaml").read_text())
            asset = goal.get("asset", "AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,JPM")
            
            try:
                market = await price.fetch(asset)
            except Exception as e:
                console.log(f"[yellow]Price fetch failed: {e}, retrying...")
                failures += 1
                if failures >= 10:
                    raise
                await asyncio.sleep(10)
                continue
            
            failures = 0
            best_match = market.get("best_match", {})
            rsi = best_match.get("rsi", 50.0)
            symbol = best_match.get("symbol", "AAPL")
            latest_price = market.get("prices", {}).get(symbol, {}).get("price")
            
            if not latest_price:
                console.log(f"[yellow]No price for {symbol}, retrying...")
                await asyncio.sleep(10)
                continue
            
            console.log(f"[green]{symbol} @ {latest_price} rsi={rsi:.2f}")
            
            (STATE / "heartbeat.json").write_text(json.dumps({"ts": int(time.time()), "symbol": symbol, "price": latest_price, "rsi": round(rsi, 2)}))
            
            await asyncio.sleep(60)
        except Exception as e:
            console.log(f"[red]Fatal: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())
