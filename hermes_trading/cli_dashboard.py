import sys
from pathlib import Path
from datetime import datetime, UTC
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box
import json
import time

from .dashboard import load_state, calculate_metrics


def format_pnl(pnl: float) -> str:
    color = "green" if pnl > 0 else "red" if pnl < 0 else "white"
    return f"[{color}]{pnl:+.2f}%[/{color}]"


def format_price(price) -> str:
    if isinstance(price, (int, float)):
        return f"${price:.2f}"
    return str(price)


def display_dashboard(state_dir: Path = None, watch: bool = False) -> None:
    console = Console()

    if state_dir is None:
        state_dir = Path(__file__).resolve().parents[1] / "state"

    while True:
        console.clear()

        state_data = load_state(state_dir)
        trades = state_data["trades"]
        heartbeat = state_data["heartbeat"]
        strategy = state_data["strategy"]
        goal = state_data["goal"]
        metrics = calculate_metrics(trades)

        current_price = heartbeat.get("price", "N/A")
        current_rsi = heartbeat.get("rsi", "N/A")
        current_symbol = heartbeat.get("symbol", "AAPL")
        current_ts = heartbeat.get("ts", int(datetime.now(UTC).timestamp()))

        last_update = datetime.fromtimestamp(current_ts, UTC).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

        console.print(
            f"\n[bold green]🤖 Trading Bot Dashboard[/bold green] [dim]({last_update})[/dim]\n"
        )

        grid = Table.grid(padding=(0, 2))

        stats_table = Table(title="Current Stats", box=box.ROUNDED)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")

        stats_table.add_row("Price", format_price(current_price))
        stats_table.add_row("Symbol", f"[bold]{current_symbol}[/bold]")
        stats_table.add_row("RSI", str(current_rsi))
        stats_table.add_row("Total P&L", format_pnl(metrics["total_pnl"]))
        stats_table.add_row(
            "Win Rate",
            f"[green]{metrics['win_rate']:.1f}%[/green] ({metrics['wins']}W/{metrics['losses']}L)",
        )

        grid.add_row(stats_table)

        strategy_table = Table(title="Strategy", box=box.ROUNDED)
        strategy_table.add_column("Setting", style="cyan")
        strategy_table.add_column("Value", style="green")

        version = strategy.get("version", "?")
        threshold = strategy.get("entry", {}).get("threshold", "?")
        stop_loss = strategy.get("stop_loss_pct", "?")
        target_return = goal.get("target_return_30d", 0) * 100

        strategy_table.add_row("Version", str(version))
        strategy_table.add_row("Entry Threshold (RSI)", str(threshold))
        strategy_table.add_row("Stop Loss", f"{stop_loss}%")
        strategy_table.add_row("Target Return (30d)", f"{target_return:.1f}%")
        strategy_table.add_row("Total Trades", str(metrics["total_trades"]))

        console.print(grid)
        console.print()
        console.print(strategy_table)
        console.print()

        if trades:
            trades_table = Table(title="Recent Trades", box=box.ROUNDED)
            trades_table.add_column("Time", style="dim")
            trades_table.add_column("Symbol", style="cyan")
            trades_table.add_column("Entry", style="white")
            trades_table.add_column("Exit", style="white")
            trades_table.add_column("P&L", style="bold")

            for trade in reversed(trades[-8:]):
                symbol = trade.get("symbol", "?")
                entry = format_price(trade.get("entry_price", 0))
                exit_price = format_price(trade.get("exit_price", 0))
                pnl = trade.get("pnl_pct", 0)
                trade_time = datetime.fromtimestamp(
                    trade.get("ts", 0), UTC
                ).strftime("%m-%d %H:%M")

                pnl_str = format_pnl(pnl)

                trades_table.add_row(trade_time, symbol, entry, exit_price, pnl_str)

            console.print(trades_table)
        else:
            console.print(
                Panel(
                    "[yellow]No trades yet - waiting for entry signals[/yellow]",
                    title="Trades",
                )
            )

        console.print()
        console.print("[dim]Press Ctrl+C to exit[/dim]")

        if not watch:
            break

        try:
            time.sleep(5)
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard stopped[/yellow]")
            sys.exit(0)


if __name__ == "__main__":
    watch = "--watch" in sys.argv or "-w" in sys.argv
    display_dashboard(watch=watch)
