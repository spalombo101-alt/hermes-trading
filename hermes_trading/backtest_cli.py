import argparse
import json
from pathlib import Path

import yaml

from .backtest import backtest

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"


def main():
    parser = argparse.ArgumentParser(description="Backtest a strategy on historical data")
    parser.add_argument(
        "--symbols",
        default="AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,JPM",
        help="Comma-separated list of symbols to backtest",
    )
    parser.add_argument("--days", type=int, default=90, help="Number of days of historical data")
    parser.add_argument("--version", type=str, help="Strategy version to test (default: current)")
    parser.add_argument("--threshold", type=int, help="Entry RSI threshold override")
    args = parser.parse_args()

    goal = yaml.safe_load((STATE / "goal.yaml").read_text())
    if args.version:
        strategy_path = STATE / "history" / f"v{args.version}.yaml"
        if not strategy_path.exists():
            print(f"Strategy version v{args.version} not found")
            return
        strategy = yaml.safe_load(strategy_path.read_text())
    else:
        strategy = yaml.safe_load((STATE / "strategy.yaml").read_text())

    if args.threshold:
        strategy["entry"]["threshold"] = args.threshold

    symbols = [s.strip() for s in args.symbols.split(",")]

    print(f"\nBacktesting {len(symbols)} symbols over {args.days} days")
    print(f"Strategy: {strategy.get('version', 'current')}")
    print(f"  Entry RSI threshold: {strategy.get('entry', {}).get('threshold')}")
    print(f"  Stop loss: {strategy.get('stop_loss_pct')}%")
    print(f"  Position size: {strategy.get('position_size_r')}R\n")

    result = backtest(symbols, strategy, goal, days=args.days)

    print(result["summary"])
    print(f"\nDetailed trades ({len(result['trades'])} total):")
    for trade in result["trades"]:
        direction = "profit" if trade["pnl_pct"] > 0 else "loss"
        print(f"  {trade['symbol']:5} entry={trade['entry_price']:8.2f} exit={trade['exit_price']:8.2f} pnl={trade['pnl_pct']:7.3f}% ({direction})")

    print(f"\nMetrics:")
    for key, val in result["metrics"].items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
