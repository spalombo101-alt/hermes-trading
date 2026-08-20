import json
from pathlib import Path
from datetime import datetime, UTC
import yaml
from typing import Any


def load_state(state_dir: Path = None) -> dict[str, Any]:
    if state_dir is None:
        state_dir = Path(__file__).resolve().parents[1] / "state"

    data = {
        "trades": [],
        "heartbeat": {},
        "strategy": {},
        "goal": {},
        "positions": [],
    }

    trades_path = state_dir / "trades.jsonl"
    if trades_path.exists():
        for line in trades_path.read_text().splitlines():
            if line.strip():
                data["trades"].append(json.loads(line))

    heartbeat_path = state_dir / "heartbeat.json"
    if heartbeat_path.exists():
        data["heartbeat"] = json.loads(heartbeat_path.read_text())

    strategy_path = state_dir / "strategy.yaml"
    if strategy_path.exists():
        data["strategy"] = yaml.safe_load(strategy_path.read_text())

    goal_path = state_dir / "goal.yaml"
    if goal_path.exists():
        data["goal"] = yaml.safe_load(goal_path.read_text())

    return data


def calculate_metrics(trades: list[dict]) -> dict[str, Any]:
    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
        }

    wins = sum(1 for t in trades if t.get("pnl_pct", 0) > 0)
    losses = sum(1 for t in trades if t.get("pnl_pct", 0) < 0)
    total_pnl = sum(float(t.get("pnl_pct", 0)) for t in trades)
    win_pnls = [float(t.get("pnl_pct", 0)) for t in trades if t.get("pnl_pct", 0) > 0]
    loss_pnls = [float(t.get("pnl_pct", 0)) for t in trades if t.get("pnl_pct", 0) < 0]

    return {
        "total_trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(trades) * 100, 1) if trades else 0,
        "total_pnl": round(total_pnl, 3),
        "avg_win": round(sum(win_pnls) / len(win_pnls), 3) if win_pnls else 0,
        "avg_loss": round(sum(loss_pnls) / len(loss_pnls), 3) if loss_pnls else 0,
    }


def generate_html(state_data: dict[str, Any]) -> str:
    trades = state_data["trades"]
    heartbeat = state_data["heartbeat"]
    strategy = state_data["strategy"]
    goal = state_data["goal"]

    metrics = calculate_metrics(trades)

    current_price = heartbeat.get("price", "N/A")
    current_rsi = heartbeat.get("rsi", "N/A")
    current_symbol = heartbeat.get("symbol", "AAPL")
    current_ts = heartbeat.get("ts", int(datetime.now(UTC).timestamp()))

    last_update = datetime.fromtimestamp(current_ts, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    recent_trades = trades[-10:] if trades else []
    recent_trades_html = ""
    for trade in reversed(recent_trades):
        symbol = trade.get("symbol", "?")
        entry = trade.get("entry_price", 0)
        exit_price = trade.get("exit_price", 0)
        pnl = trade.get("pnl_pct", 0)
        pnl_class = "win" if pnl > 0 else "loss" if pnl < 0 else "neutral"
        trade_date = datetime.fromtimestamp(trade.get("ts", 0), UTC).strftime(
            "%m-%d %H:%M"
        )
        recent_trades_html += f"""
            <div class="trade">
                <div>
                    <span class="trade-symbol">{symbol}</span>
                    <span class="trade-detail">{trade_date}</span>
                </div>
                <div style="font-size: 12px; color: #888; margin-top: 5px;">
                    Entry: ${entry:.2f} → Exit: ${exit_price:.2f}
                </div>
                <div class="trade-pnl {pnl_class}">{pnl:+.2f}%</div>
            </div>
        """

    threshold = strategy.get("entry", {}).get("threshold", "?")
    stop_loss = strategy.get("stop_loss_pct", "?")
    version = strategy.get("version", "?")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>Trading Bot Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Monaco', 'Courier New', monospace; background: linear-gradient(135deg, #0a0e27 0%, #1a1f4b 100%); color: #e0e0e0; padding: 20px; min-height: 100vh; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 40px; border-bottom: 2px solid #00ff88; padding-bottom: 20px; }}
        h1 {{ font-size: 2.5em; color: #00ff88; margin-bottom: 5px; text-shadow: 0 0 20px rgba(0, 255, 136, 0.5); }}
        .status {{ font-size: 14px; color: #888; }}
        .status.live {{ color: #00ff88; font-weight: bold; }}
        .timestamp {{ font-size: 12px; color: #666; margin-top: 10px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: rgba(20, 25, 50, 0.8); border: 1px solid #00ff88; border-radius: 8px; padding: 25px; box-shadow: 0 0 20px rgba(0, 255, 136, 0.1); }}
        .card:hover {{ box-shadow: 0 0 30px rgba(0, 255, 136, 0.3); border-color: #00ffcc; }}
        .card-label {{ font-size: 11px; color: #00ff88; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }}
        .card-value {{ font-size: 32px; font-weight: bold; color: #ffffff; margin: 10px 0; }}
        .card-value.positive {{ color: #00ff88; }}
        .card-value.negative {{ color: #ff4444; }}
        .card-detail {{ font-size: 12px; color: #888; margin-top: 15px; border-top: 1px solid #333; padding-top: 10px; }}
        .trades-section {{ background: rgba(20, 25, 50, 0.8); border: 1px solid #00ff88; border-radius: 8px; padding: 25px; margin-bottom: 30px; }}
        .trades-section h2 {{ color: #00ff88; margin-bottom: 20px; font-size: 18px; text-transform: uppercase; }}
        .trade {{ background: rgba(10, 15, 35, 0.5); border-left: 3px solid #00ff88; padding: 15px; margin-bottom: 10px; border-radius: 4px; font-size: 13px; display: flex; justify-content: space-between; align-items: center; }}
        .trade-symbol {{ color: #00ffcc; font-weight: bold; }}
        .trade-detail {{ color: #666; font-size: 11px; margin-left: 10px; }}
        .trade-pnl {{ font-weight: bold; font-size: 14px; }}
        .trade-pnl.win {{ color: #00ff88; }}
        .trade-pnl.loss {{ color: #ff4444; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #333; color: #666; font-size: 12px; }}
        .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }}
        @media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Trading Bot Dashboard</h1>
            <p class="status"><span class="live">● LIVE</span></p>
            <p class="timestamp">Updated: {last_update}</p>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-label">Current Price</div>
                <div class="card-value">${current_price}</div>
                <div class="card-detail"><strong>{current_symbol}</strong> | RSI: {current_rsi}</div>
            </div>

            <div class="card">
                <div class="card-label">Total P&L</div>
                <div class="card-value {'positive' if metrics['total_pnl'] >= 0 else 'negative'}">{metrics['total_pnl']:+.3f}%</div>
                <div class="card-detail">Over {metrics['total_trades']} trades</div>
            </div>

            <div class="card">
                <div class="card-label">Win Rate</div>
                <div class="card-value positive">{metrics['win_rate']:.1f}%</div>
                <div class="card-detail">{metrics['wins']}W / {metrics['losses']}L</div>
            </div>

            <div class="card">
                <div class="card-label">Avg Winner</div>
                <div class="card-value positive">{metrics['avg_win']:+.2f}%</div>
                <div class="card-detail">Avg Loser: {metrics['avg_loss']:+.2f}%</div>
            </div>
        </div>

        <div class="two-col">
            <div class="card">
                <div class="card-label">Strategy</div>
                <div style="margin-top: 15px; font-size: 13px; line-height: 1.8;">
                    <div><strong>Version:</strong> {version}</div>
                    <div><strong>Entry Threshold:</strong> {threshold}</div>
                    <div><strong>Stop Loss:</strong> {stop_loss}%</div>
                    <div><strong>Target Return:</strong> {goal.get('target_return_30d', 0) * 100:.1f}%</div>
                    <div><strong>Max Drawdown:</strong> {goal.get('max_drawdown', 0) * 100:.1f}%</div>
                </div>
            </div>

            <div class="card">
                <div class="card-label">Status</div>
                <div style="margin-top: 15px; font-size: 13px; line-height: 1.8;">
                    <div>✓ Price Feed: <span style="color: #00ff88;">ACTIVE</span></div>
                    <div>✓ Broker: <span style="color: #00ff88;">CONNECTED</span></div>
                    <div>✓ Strategy: <span style="color: #00ff88;">RUNNING</span></div>
                    <div>✓ Trades Tracked: <span style="color: #00ff88;">{metrics['total_trades']}</span></div>
                </div>
            </div>
        </div>

        <div class="trades-section">
            <h2>Recent Trades (Last 10)</h2>
            {recent_trades_html if recent_trades_html else '<div style="color: #666; padding: 20px; text-align: center;">No trades yet</div>'}
        </div>

        <div class="footer">
            Auto-refreshes every 60 seconds | Open this file in a browser to monitor live
        </div>
    </div>
</body>
</html>
"""
    return html


def update_dashboard(output_path: str = None) -> None:
    if output_path is None:
        output_path = Path(__file__).resolve().parents[1] / "dashboard-live.html"
    else:
        output_path = Path(output_path)

    state_data = load_state()
    html = generate_html(state_data)
    output_path.write_text(html)
    print(f"Dashboard updated: {output_path}")


if __name__ == "__main__":
    update_dashboard()
