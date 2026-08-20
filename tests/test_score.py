import pytest
from hermes_trading.score import score, _returns, _drawdown


@pytest.fixture
def basic_goal():
    return {
        "target_return_30d": 0.05,
        "max_drawdown": 0.05,
        "min_sharpe": 1.2,
        "failure_below": -0.04,
    }


class TestReturns:
    def test_returns_empty_trades(self):
        trades = []
        rs = _returns(trades)
        assert rs == []

    def test_returns_single_trade(self):
        trades = [{"pnl_pct": 2.0}]
        rs = _returns(trades)
        assert len(rs) == 1
        assert abs(rs[0] - 0.02) < 0.0001

    def test_returns_multiple_trades(self):
        trades = [
            {"pnl_pct": 1.0},
            {"pnl_pct": -0.5},
            {"pnl_pct": 2.5},
        ]
        rs = _returns(trades)
        assert len(rs) == 3
        assert rs[0] == 0.01
        assert rs[1] == -0.005
        assert rs[2] == 0.025

    def test_returns_ignores_missing_pnl(self):
        trades = [
            {"pnl_pct": 1.0},
            {"symbol": "TEST"},
            {"pnl_pct": 2.0},
        ]
        rs = _returns(trades)
        assert len(rs) == 2


class TestDrawdown:
    def test_drawdown_flat_equity(self):
        equity = [1.0, 1.0, 1.0, 1.0]
        dd = _drawdown(equity)
        assert dd == 0.0

    def test_drawdown_up_only(self):
        equity = [1.0, 1.01, 1.02, 1.03]
        dd = _drawdown(equity)
        assert dd == 0.0

    def test_drawdown_down_from_peak(self):
        equity = [1.0, 1.1, 0.95, 1.05]
        dd = _drawdown(equity)
        assert dd > 0
        expected_dd = (1.1 - 0.95) / 1.1
        assert abs(dd - expected_dd) < 0.001


class TestScore:
    def test_score_no_trades(self, basic_goal):
        trades = []
        s = score(trades, basic_goal)
        assert s == 0.0

    def test_score_winning_trade(self, basic_goal):
        trades = [{"pnl_pct": 5.0}]
        s = score(trades, basic_goal)
        assert s > 0

    def test_score_losing_trade(self, basic_goal):
        trades = [{"pnl_pct": -5.0}]
        s = score(trades, basic_goal)
        assert s < 0

    def test_score_below_failure_threshold(self, basic_goal):
        trades = [{"pnl_pct": -5.0}]
        goal = basic_goal.copy()
        goal["failure_below"] = -0.04
        s = score(trades, goal)
        assert s < -0.5

    def test_score_meets_target(self, basic_goal):
        trades = [{"pnl_pct": 2.0} for _ in range(5)]
        s = score(trades, basic_goal)
        assert isinstance(s, float)
        assert -1.0 <= s <= 1.0

    def test_score_bounds(self, basic_goal):
        trades = [{"pnl_pct": 100.0} for _ in range(10)]
        s = score(trades, basic_goal)
        assert -1.0 <= s <= 1.0

    def test_score_consistency(self, basic_goal):
        trades = [
            {"pnl_pct": 1.5},
            {"pnl_pct": 2.0},
            {"pnl_pct": -0.5},
        ]
        s1 = score(trades, basic_goal)
        s2 = score(trades, basic_goal)
        assert s1 == s2
