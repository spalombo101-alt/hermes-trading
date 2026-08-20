from __future__ import annotations

import os
import time
from typing import Any

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest, StopLossRequest, TakeProfitRequest

_client: TradingClient | None = None


class BrokerError(RuntimeError):
    pass


def _is_paper_mode() -> bool:
    mode = os.environ.get("HERMES_TRADING_MODE", "paper").lower()
    accepted_risk = os.environ.get("HERMES_TRADING_I_ACCEPT_RISK", "false").lower() == "true"
    return not (mode == "live" and accepted_risk)


def client() -> TradingClient:
    global _client
    if _client is None:
        key = os.environ.get("ALPACA_API_KEY")
        secret = os.environ.get("ALPACA_API_SECRET")
        if not key or not secret:
            raise BrokerError("ALPACA_API_KEY / ALPACA_API_SECRET are not set")
        paper = _is_paper_mode()
        url_override = "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
        _client = TradingClient(key, secret, paper=paper, url_override=url_override)
    return _client


def account() -> dict[str, float]:
    acct = client().get_account()
    return {
        "equity": float(acct.equity),
        "cash": float(acct.cash),
        "buying_power": float(acct.buying_power),
    }


def get_open_position(symbol: str) -> dict[str, Any] | None:
    try:
        pos = client().get_open_position(symbol)
    except Exception:
        return None
    return {
        "symbol": pos.symbol,
        "qty": float(pos.qty),
        "avg_entry_price": float(pos.avg_entry_price),
        "unrealized_plpc": float(pos.unrealized_plpc),
    }


def get_all_positions() -> list[dict[str, Any]]:
    positions = client().get_all_positions()
    return [{"symbol": p.symbol, "qty": float(p.qty), "avg_entry_price": float(p.avg_entry_price)} for p in positions]


def has_open_position() -> bool:
    return len(client().get_all_positions()) > 0


def submit_bracket_order(
    symbol: str,
    qty: int,
    take_profit_price: float,
    stop_loss_price: float,
    strategy_version: str,
) -> dict[str, Any]:
    client_order_id = f"hermes-v{strategy_version}-{int(time.time())}"
    request = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
        order_class=OrderClass.BRACKET,
        client_order_id=client_order_id,
        take_profit=TakeProfitRequest(limit_price=round(take_profit_price, 2)),
        stop_loss=StopLossRequest(stop_price=round(stop_loss_price, 2)),
    )
    order = client().submit_order(request)
    return {"id": str(order.id), "client_order_id": order.client_order_id, "symbol": symbol, "qty": qty}


def list_newly_closed_trades(after: float) -> list[dict[str, Any]]:
    """Reconcile filled bracket orders into (entry, exit, pnl) trade records.

    Alpaca fills the entry leg and one of the OCO exit legs (take-profit or
    stop-loss) independently, so a trade is only "closed" once one exit leg
    is filled. `client_order_id` carries the strategy version that placed
    the entry, since Alpaca has no concept of our strategy versioning.
    """
    request = GetOrdersRequest(
        status=QueryOrderStatus.CLOSED,
        after=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(after)),
        limit=200,
        nested=True,
    )
    orders = client().get_orders(request)
    trades = []
    for order in orders:
        if order.order_class != OrderClass.BRACKET or not order.filled_avg_price:
            continue
        filled_leg = next((leg for leg in (order.legs or []) if leg.filled_avg_price), None)
        if filled_leg is None:
            continue
        entry_price = float(order.filled_avg_price)
        exit_price = float(filled_leg.filled_avg_price)
        strategy_version = (order.client_order_id or "hermes-v00-0").split("-v")[-1].split("-")[0]
        trades.append(
            {
                "ts": int(filled_leg.filled_at.timestamp()) if filled_leg.filled_at else int(time.time()),
                "symbol": order.symbol,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl_pct": round((exit_price - entry_price) / entry_price * 100, 3),
                "strategy": strategy_version,
                "order_id": str(order.id),
            }
        )
    return trades
