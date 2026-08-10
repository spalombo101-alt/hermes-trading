from __future__ import annotations
import math
from typing import Iterable

def _returns(trades: Iterable[dict]) -> list[float]:
    vals = []
    for trade in trades:
        pnl = trade.get("pnl_pct")
        if pnl is not None:
            vals.append(float(pnl) / 100.0)
    return vals

def _drawdown(equity: list[float]) -> float:
    peak = equity[0] if equity else 1.0
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        worst = min(worst, (value - peak) / peak)
    return abs(worst)

def score(trades, goal) -> float:
    rs = _returns(trades)
    if not rs:
        return 0.0
    realised = math.prod([1 + r for r in rs]) - 1
    equity = [1.0]
    for r in rs:
        equity.append(equity[-1] * (1 + r))
    dd = _drawdown(equity)
    mean = sum(rs) / len(rs)
    variance = sum((r - mean) ** 2 for r in rs) / max(len(rs) - 1, 1)
    sharpe = 0.0 if variance == 0 else mean / math.sqrt(variance) * math.sqrt(min(365, len(rs) * 24))

    target_component = max(-1.0, min(1.0, realised / float(goal["target_return_30d"])))
    dd_component = 1.0 - max(0.0, dd / float(goal["max_drawdown"]))
    dd_component = max(-1.0, min(1.0, dd_component))
    sharpe_component = max(-1.0, min(1.0, sharpe / float(goal["min_sharpe"])))
    total = 0.5 * target_component + 0.3 * dd_component + 0.2 * sharpe_component
    if realised < float(goal.get("failure_below", -0.04)):
        total -= 0.25
    return max(-1.0, min(1.0, total))
