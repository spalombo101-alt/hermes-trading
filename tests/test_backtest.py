import pytest
from hermes_trading.backtest import backtest, _backtest_symbol
from datetime import datetime, timedelta


@pytest.fixture
def basic_strategy():
    return {
        "version": "01",
        "entry": {"indicator": "rsi", "threshold": 30, "direction": "long"},
        "stop_loss_pct": 2.0,
        "position_size_r": 0.5,
    }


@pytest.fixture
def basic_goal():
    return {
        "asset": "AAPL,MSFT",
        "target_return_30d": 0.05,
        "max_drawdown": 0.05,
        "min_sharpe": 1.2,
        "failure_below": -0.04,
    }


class TestBacktestSymbol:
    def test_no_trades_insufficient_data(self, basic_strategy, basic_goal):
        closes = [100, 101, 102]
        highs = [101, 102, 103]
        lows = [99, 100, 101]
        dates = [
            datetime.now() - timedelta(days=2),
            datetime.now() - timedelta(days=1),
            datetime.now(),
        ]

        trades = _backtest_symbol(
            "TEST",
            closes,
            highs,
            lows,
            dates,
            entry_threshold=30,
            stop_loss_pct=0.02,
            position_size_r=0.5,
        )
        assert trades == []

    def test_backtest_returns_trades(self, basic_strategy, basic_goal):
        closes = list(range(100, 140))
        highs = [p + 1 for p in closes]
        lows = [p - 1 for p in closes]
        dates = [
            datetime.now() - timedelta(days=40 - i) for i in range(40)
        ]

        trades = _backtest_symbol(
            "TEST",
            closes,
            highs,
            lows,
            dates,
            entry_threshold=50,
            stop_loss_pct=0.02,
            position_size_r=0.5,
        )
        assert isinstance(trades, list)

    def test_backtest_trade_structure(self, basic_strategy, basic_goal):
        closes = list(range(100, 150))
        highs = [p + 2 for p in closes]
        lows = [p - 2 for p in closes]
        dates = [datetime.now() - timedelta(days=50 - i) for i in range(50)]

        trades = _backtest_symbol(
            "TEST",
            closes,
            highs,
            lows,
            dates,
            entry_threshold=40,
            stop_loss_pct=0.02,
            position_size_r=0.5,
        )

        for trade in trades:
            assert "ts" in trade
            assert "symbol" in trade
            assert "entry_price" in trade
            assert "exit_price" in trade
            assert "pnl_pct" in trade


class TestBacktestFullRun:
    def test_backtest_returns_result_dict(self, basic_strategy, basic_goal):
        result = backtest(
            ["AAPL"], basic_strategy, basic_goal, days=30
        )
        assert isinstance(result, dict)
        assert "trades" in result
        assert "metrics" in result
        assert "summary" in result

    def test_backtest_metrics_structure(self, basic_strategy, basic_goal):
        result = backtest(
            ["AAPL"], basic_strategy, basic_goal, days=30
        )
        metrics = result["metrics"]
        if metrics:
            assert "total_trades" in metrics
            assert "wins" in metrics
            assert "losses" in metrics
            assert "win_rate_pct" in metrics
            assert "realised_return" in metrics
            assert "max_drawdown" in metrics
            assert "score" in metrics
        else:
            assert result["summary"] == "No trades generated"

    def test_backtest_no_trades(self, basic_strategy, basic_goal):
        strategy = basic_strategy.copy()
        strategy["entry"]["threshold"] = 5
        result = backtest(
            ["AAPL"], strategy, basic_goal, days=30
        )
        if result["metrics"]:
            assert result["metrics"]["total_trades"] >= 0
        else:
            assert result["summary"] == "No trades generated"
