import asyncio
import json
import time
from pathlib import Path
import yaml
from rich.console import Console
from .adapters import broker, price
from .friendly import write_summary

console = Console()


def _load_checkpoint(path: Path) -> float:
    if path.exists():
        return json.loads(path.read_text()).get("last_check_ts", time.time() - 86400)
    return time.time() - 86400


def _save_checkpoint(path: Path, ts: float) -> None:
    path.write_text(json.dumps({"last_check_ts": ts}))


def _logged_order_ids(trades_path: Path) -> set[str]:
    if not trades_path.exists():
        return set()
    ids = set()
    for line in trades_path.read_text().splitlines():
        if line.strip():
            ids.add(json.loads(line).get("order_id"))
    return ids


def _reconcile_closed_trades(state: Path, checkpoint_path: Path) -> None:
    last_check = _load_checkpoint(checkpoint_path)
    now = time.time()
    try:
        closed = broker.list_newly_closed_trades(after=last_check)
    except Exception as e:
        console.log(f"[red]Failed to reconcile broker trades: {e}")
        return
    already_logged = _logged_order_ids(state / "trades.jsonl")
    new_trades = [t for t in closed if t["order_id"] not in already_logged]
    if new_trades:
        with (state / "trades.jsonl").open("a") as f:
            for t in new_trades:
                f.write(json.dumps(t) + "\n")
                color = "green" if t["pnl_pct"] >= 0 else "red"
                console.log(f"[{color}]closed {t['symbol']} pnl={t['pnl_pct']:.3f}%")
    _save_checkpoint(checkpoint_path, now)


async def _submit_order_with_retry(
    symbol: str, qty: int, take_profit_price: float, stop_loss_price: float, strategy_version: str, max_retries: int = 3
) -> bool:
    for attempt in range(max_retries):
        try:
            order = broker.submit_bracket_order(symbol, qty, take_profit_price, stop_loss_price, strategy_version)
            console.log(f"[cyan]ENTRY {symbol} qty={qty} @ (market) rsi entry order={order['id']}")
            return True
        except Exception as e:
            console.log(f"[yellow]Order submission failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                console.log(f"[red]Failed to submit order for {symbol} after {max_retries} attempts")
                return False


async def main():
    ROOT = Path(__file__).resolve().parents[1]
    STATE = ROOT / "state"
    checkpoint_path = STATE / "broker_checkpoint.json"

    console.log("[cyan]Booting hermes-trading worker (multi-position, Alpaca paper)")

    failures = 0
    max_concurrent_positions = 3

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
            symbol = best_match.get("symbol", "AAPL")
            prices = market.get("prices", {})
            symbol_data = prices.get(symbol, {})
            latest_price = symbol_data.get("price")

            if not latest_price:
                console.log(f"[yellow]No price for {symbol}")
                await asyncio.sleep(60)
                continue

            _reconcile_closed_trades(STATE, checkpoint_path)

            try:
                account = broker.account()
                open_positions = broker.get_all_positions()
                num_open = len(open_positions)
            except broker.BrokerError as e:
                console.log(f"[red]Broker not configured: {e}")
                await asyncio.sleep(60)
                continue
            except Exception as e:
                console.log(f"[red]Failed to read broker account: {e}")
                await asyncio.sleep(60)
                continue

            if num_open < max_concurrent_positions:
                entry_config = strategy.get("entry", {})
                threshold = entry_config.get("threshold", 30)
                rsi = symbol_data.get("rsi", 50.0)
                histogram = symbol_data.get("histogram", 0.0)

                entry_ready = rsi <= threshold and histogram <= 1.0

                if entry_ready:
                    stop_loss_pct = strategy.get("stop_loss_pct", 2.0) / 100.0
                    stop_price = latest_price * (1 - stop_loss_pct)
                    take_profit_price = latest_price * 1.02
                    risk_per_share = latest_price - stop_price
                    atr = symbol_data.get("atr", 0.0)
                    volatility_multiplier = max(0.5, min(2.0, 1.0 if atr == 0 else 14.0 / atr))
                    risk_fraction = strategy.get("position_size_r", 0.5) / 100.0 * volatility_multiplier
                    equity = account["equity"]
                    qty = int((equity * risk_fraction) / risk_per_share) if risk_per_share > 0 else 0

                    if qty < 1:
                        console.log(f"[yellow]Position size too small for {symbol} at {latest_price} (equity={equity:.2f})")
                    else:
                        await _submit_order_with_retry(
                            symbol, qty, take_profit_price, stop_price, str(strategy.get("version", "00"))
                        )

            now = int(time.time())
            rsi = symbol_data.get("rsi", 50.0)
            (STATE / "heartbeat.json").write_text(json.dumps({"ts": now, "symbol": symbol, "price": latest_price, "rsi": round(rsi, 2)}))
            write_summary(STATE)

            await asyncio.sleep(60)
        except Exception as e:
            console.log(f"[red]Fatal: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
