import asyncio
import json
import os
import time
from pathlib import Path
import yaml
from rich.console import Console
from .adapters import price
from .friendly import write_summary

console = Console()

async def main():
    ROOT = Path(__file__).resolve().parents[1]
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
                console.log(f"[red]Failed to fetch prices: {e}")
                failures += 1
                if failures >= 5:
                    raise
                await asyncio.sleep(60)
                continue
            
            failures = 0
            
            best_match = market.get("best_match", {})
            rsi = best_match.get("rsi", 50.0)
            symbol = best_match.get("symbol", "AAPL")
            prices = market.get("prices", {})
            latest_price = prices.get(symbol, {}).get("price")
            
            if not latest_price:
                console.log(f"[yellow]No price for {symbol}")
                await asyncio.sleep(60)
                continue
            
            if open_position:
                entry_price = open_position["entry_price"]
                stop_loss_pct = strategy.get("stop_loss_pct", 2.0) / 100.0
                stop_price = entry_price * (1 - stop_loss_pct)
                
                if latest_price <= stop_price:
                    pnl_pct = ((latest_price - entry_price) / entry_price) * 100
                    (STATE / "trades.jsonl").open("a").write(json.dumps({"ts": int(time.time()), "symbol": symbol, "entry_price": entry_price, "exit_price": latest_price, "pnl_pct": round(pnl_pct, 3), "strategy": strategy.get("version")}) + "\n")
                    console.log(f"[red]closed {symbol} pnl={pnl_pct:.3f}%")
                    open_position = None
                elif latest_price > entry_price * 1.02:
                    pnl_pct = 2.0
                    (STATE / "trades.jsonl").open("a").write(json.dumps({"ts": int(time.time()), "symbol": symbol, "entry_price": entry_price, "exit_price": latest_price, "pnl_pct": 2.0, "strategy": strategy.get("version")}) + "\n")
                    console.log(f"[green]closed {symbol} pnl=2.000%")
                    open_position = None
            else:
                entry_config = strategy.get("entry", {})
                threshold = entry_config.get("threshold", 30)
                
                if rsi <= threshold:
                    open_position = {"symbol": symbol, "entry_price": latest_price, "ts": int(time.time())}
                    console.log(f"[cyan]ENTRY {symbol} @ {latest_price} rsi={rsi:.2f}")
            
            now = int(time.time())
            (STATE / "heartbeat.json").write_text(json.dumps({"ts": now, "symbol": symbol, "price": latest_price, "rsi": round(rsi, 2)}))
            write_summary(STATE)
            
            await asyncio.sleep(60)
        except Exception as e:
            console.log(f"[red]Fatal: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())
