from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def money_direction(value: float) -> str:
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def describe_rsi(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value <= 30:
        return "the bot thinks the coin may be temporarily beaten down"
    if value >= 70:
        return "the coin looks hot and possibly stretched"
    return "the coin looks fairly neutral"


def describe_strategy(strategy: dict[str, Any]) -> str:
    threshold = strategy.get("entry", {}).get("threshold", "?")
    stop = strategy.get("stop_loss_pct", "?")
    size = strategy.get("position_size_r", "?")
    version = strategy.get("version", "?")
    return (
        f"Version {version}: the bot looks for moments when the market seems weak or oversold "
        f"and may buy if its simple momentum gauge falls to {threshold} or below. "
        f"It uses a {stop}% paper stop-loss and a small test position size of {size}R."
    )


def generate_summary(state_dir: Path = STATE) -> str:
    goal = yaml.safe_load((state_dir / "goal.yaml").read_text())
    strategy = yaml.safe_load((state_dir / "strategy.yaml").read_text())
    trades = load_jsonl(state_dir / "trades.jsonl")
    hypotheses = load_jsonl(state_dir / "hypotheses.jsonl")
    heartbeat_path = state_dir / "heartbeat.json"
    heartbeat = json.loads(heartbeat_path.read_text()) if heartbeat_path.exists() else {}

    asset = goal.get("asset", "the selected asset")
    target = float(goal.get("target_return_30d", 0)) * 100
    max_dd = float(goal.get("max_drawdown", 0)) * 100
    reflection_every = int(goal.get("reflection_every", 5))
    closed = len(trades)
    total_pnl = sum(float(t.get("pnl_pct", 0)) for t in trades)
    wins = sum(1 for t in trades if float(t.get("pnl_pct", 0)) > 0)
    losses = sum(1 for t in trades if float(t.get("pnl_pct", 0)) < 0)
    last_price = heartbeat.get("last")
    current_rsi = heartbeat.get("rsi")
    open_position = heartbeat.get("open_position")
    trades_until_reflection = max(0, reflection_every - (closed % reflection_every or reflection_every)) if closed else reflection_every
    if closed and closed % reflection_every == 0:
        trades_until_reflection = 0

    lines = [
        "# Trading Agent Status — Plain English",
        "",
        f"Updated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Big Picture",
        "",
        f"This is a paper-trading bot watching **{asset}**. Paper trading means it is practicing with fake trades, not risking real money.",
        f"The goal is to learn a strategy that could make about **{target:.1f}% over 30 days** while avoiding losses worse than **{max_dd:.1f}%**.",
        "",
        "## What The Bot Is Doing Right Now",
        "",
        f"- Latest price seen: **{last_price:,.2f}**" if isinstance(last_price, (int, float)) else "- Latest price seen: not available yet",
        f"- Market read: **{describe_rsi(float(current_rsi))}**" if current_rsi is not None else "- Market read: not available yet",
        f"- Current paper position: **{'open' if open_position else 'none'}**",
        f"- Current strategy: {describe_strategy(strategy)}",
        "",
        "## Results So Far",
        "",
        f"- Closed paper trades: **{closed}**",
        f"- Wins / losses: **{wins} wins**, **{losses} losses**",
        f"- Net paper result: **{money_direction(total_pnl)} {abs(total_pnl):.3f}%** across all closed trades",
        f"- Next strategy review: **{trades_until_reflection} more closed trade(s)**" if trades_until_reflection else "- Next strategy review: **due now**",
        "",
    ]

    if trades:
        lines.extend(["## Last 5 Trades", ""])
        for trade in trades[-5:]:
            pnl = float(trade.get("pnl_pct", 0))
            direction = "made" if pnl > 0 else "lost" if pnl < 0 else "broke even at"
            lines.append(
                f"- Strategy v{trade.get('strategy_version', '?')}: bought near **{float(trade.get('entry_price', 0)):,.2f}**, "
                f"sold near **{float(trade.get('exit_price', 0)):,.2f}**, and {direction} **{abs(pnl):.3f}%** on paper."
            )
        lines.append("")

    lines.extend(["## What Hermes Changed", ""])
    if hypotheses:
        latest = hypotheses[-1]
        changed = latest.get("changed", "a setting")
        prior = latest.get("prior")
        new = latest.get("new")
        reason = latest.get("reason", "No reason recorded.")
        lines.extend([
            f"Hermes last changed **{changed}** from **{prior}** to **{new}**.",
            "",
            f"Plain-English reason: {reason}.",
            "",
            "That means Hermes made one small adjustment, then kept everything else the same so we can see whether that one change helps.",
        ])
    else:
        lines.append("Hermes has not changed the strategy yet. It is waiting for enough closed paper trades to learn from.")

    lines.extend([
        "",
        "## How To Read This",
        "",
        "- A tiny gain or loss is normal right now; the bot is still learning.",
        "- The important thing is whether each version improves over multiple trades.",
        "- Because this is paper mode, nothing here is financial advice and no real money is being traded.",
        "",
    ])
    return "\n".join(lines)


def write_summary(state_dir: Path = STATE) -> Path:
    path = state_dir / "friendly-status.md"
    path.write_text(generate_summary(state_dir))
    return path


def main() -> None:
    path = write_summary()
    print(path.read_text())


if __name__ == "__main__":
    main()
