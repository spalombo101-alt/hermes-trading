from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yfinance as yf

from .adapters.price import _atr, _macd, _rsi
from .score import score


def backtest(
    symbols: list[str],
    strategy: dict[str, Any],
    goal: dict[str, Any],
    days: int = 90,
) -> dict[str, Any]:
    """Backtest a strategy on historical data.

    Args:
        symbols: List of stock symbols to test
        strategy: Strategy config (entry.threshold, stop_loss_pct, etc)
        goal: Goal config (target_return_30d, max_drawdown, etc)
        days: Historical days to use

    Returns:
        Dict with trades, metrics, and summary
    """
    all_trades = []

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f"{days}d")
            if hist.empty:
                continue

            closes = hist["Close"].tolist()
            highs = hist["High"].tolist()
            lows = hist["Low"].tolist()
            dates = hist.index.tolist()

            entry_threshold = strategy.get("entry", {}).get("threshold", 30)
            stop_loss_pct = strategy.get("stop_loss_pct", 2.0) / 100.0
            position_size_r = strategy.get("position_size_r", 0.5)

            trades_for_symbol = _backtest_symbol(
                symbol, closes, highs, lows, dates, entry_threshold, stop_loss_pct, position_size_r
            )
            all_trades.extend(trades_for_symbol)
        except Exception as e:
            print(f"Warning: Failed to backtest {symbol}: {e}")
            continue

    if not all_trades:
        return {"trades": [], "metrics": {}, "summary": "No trades generated"}

    all_trades.sort(key=lambda t: t["ts"])

    realized = sum(t.get("pnl_pct", 0) for t in all_trades) / 100.0
    equity = [1.0]
    for t in all_trades:
        equity.append(equity[-1] * (1 + float(t.get("pnl_pct", 0)) / 100.0))

    peak = equity[0]
    max_dd = 0.0
    for val in equity:
        peak = max(peak, val)
        max_dd = max(max_dd, (peak - val) / peak)

    wins = sum(1 for t in all_trades if t.get("pnl_pct", 0) > 0)
    losses = sum(1 for t in all_trades if t.get("pnl_pct", 0) < 0)
    win_rate = wins / len(all_trades) * 100 if all_trades else 0

    return {
        "trades": all_trades,
        "metrics": {
            "total_trades": len(all_trades),
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round(win_rate, 2),
            "realised_return": round(realized * 100, 3),
            "max_drawdown": round(max_dd * 100, 3),
            "final_equity": round(equity[-1], 3),
            "score": score(all_trades, goal),
        },
        "summary": f"{len(all_trades)} trades: {wins}W {losses}L ({win_rate:.1f}%) | "
        f"return {realized * 100:.2f}% | drawdown {max_dd * 100:.2f}% | score {score(all_trades, goal):.3f}",
    }


def _backtest_symbol(
    symbol: str,
    closes: list[float],
    highs: list[float],
    lows: list[float],
    dates: list,
    entry_threshold: int,
    stop_loss_pct: float,
    position_size_r: float,
) -> list[dict[str, Any]]:
    """Simulate trades for a single symbol."""
    trades = []
    open_position = None

    for i in range(1, len(closes)):
        rsi = _rsi(closes[: i + 1])
        macd, signal, histogram = _macd(closes[: i + 1])
        price = closes[i]

        if open_position:
            entry_price = open_position["entry_price"]
            stop_price = entry_price * (1 - stop_loss_pct)
            take_profit_price = entry_price * 1.02

            if price <= stop_price:
                pnl_pct = ((price - entry_price) / entry_price) * 100
                trades.append(
                    {
                        "ts": int(dates[i].timestamp()),
                        "symbol": symbol,
                        "entry_price": round(entry_price, 2),
                        "exit_price": round(price, 2),
                        "pnl_pct": round(pnl_pct, 3),
                        "reason": "stop_loss",
                    }
                )
                open_position = None
            elif price >= take_profit_price:
                trades.append(
                    {
                        "ts": int(dates[i].timestamp()),
                        "symbol": symbol,
                        "entry_price": round(entry_price, 2),
                        "exit_price": round(price, 2),
                        "pnl_pct": 2.0,
                        "reason": "take_profit",
                    }
                )
                open_position = None
        else:
            entry_ready = rsi <= entry_threshold and histogram <= 1.0
            if entry_ready:
                open_position = {"entry_price": price, "ts": dates[i]}

    return trades
