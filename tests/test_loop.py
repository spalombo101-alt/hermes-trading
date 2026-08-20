import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import time
from pathlib import Path
from hermes_trading.loop import (
    _load_checkpoint,
    _save_checkpoint,
    _logged_order_ids,
    _reconcile_closed_trades,
)


class TestCheckpoint:
    def test_load_checkpoint_missing_file(self, tmp_path):
        checkpoint_path = tmp_path / "checkpoint.json"
        result = _load_checkpoint(checkpoint_path)
        assert isinstance(result, float)
        assert result < time.time()

    def test_load_checkpoint_existing_file(self, tmp_path):
        checkpoint_path = tmp_path / "checkpoint.json"
        test_ts = time.time() - 3600
        checkpoint_path.write_text(json.dumps({"last_check_ts": test_ts}))

        result = _load_checkpoint(checkpoint_path)
        assert result == test_ts

    def test_save_checkpoint(self, tmp_path):
        checkpoint_path = tmp_path / "checkpoint.json"
        test_ts = time.time()

        _save_checkpoint(checkpoint_path, test_ts)

        loaded = json.loads(checkpoint_path.read_text())
        assert loaded["last_check_ts"] == test_ts


class TestLoggedOrderIds:
    def test_logged_order_ids_missing_file(self, tmp_path):
        trades_path = tmp_path / "trades.jsonl"
        result = _logged_order_ids(trades_path)
        assert result == set()

    def test_logged_order_ids_empty_file(self, tmp_path):
        trades_path = tmp_path / "trades.jsonl"
        trades_path.write_text("")
        result = _logged_order_ids(trades_path)
        assert result == set()

    def test_logged_order_ids_single_trade(self, tmp_path):
        trades_path = tmp_path / "trades.jsonl"
        trade = {"order_id": "order_123", "symbol": "AAPL", "pnl_pct": 2.0}
        trades_path.write_text(json.dumps(trade) + "\n")

        result = _logged_order_ids(trades_path)
        assert result == {"order_123"}

    def test_logged_order_ids_multiple_trades(self, tmp_path):
        trades_path = tmp_path / "trades.jsonl"
        trades = [
            {"order_id": "order_123", "symbol": "AAPL", "pnl_pct": 2.0},
            {"order_id": "order_456", "symbol": "MSFT", "pnl_pct": -1.5},
            {"order_id": "order_789", "symbol": "GOOGL", "pnl_pct": 3.0},
        ]
        trades_path.write_text(
            "\n".join(json.dumps(t) for t in trades) + "\n"
        )

        result = _logged_order_ids(trades_path)
        assert result == {"order_123", "order_456", "order_789"}


class TestReconcileClosedTrades:
    @patch("hermes_trading.loop.broker.list_newly_closed_trades")
    def test_reconcile_no_new_trades(self, mock_list_trades, tmp_path):
        state = tmp_path
        checkpoint_path = state / "broker_checkpoint.json"
        trades_path = state / "trades.jsonl"
        trades_path.write_text("")

        mock_list_trades.return_value = []

        _reconcile_closed_trades(state, checkpoint_path)

        loaded = json.loads(checkpoint_path.read_text())
        assert "last_check_ts" in loaded

    @patch("hermes_trading.loop.console")
    @patch("hermes_trading.loop.broker.list_newly_closed_trades")
    def test_reconcile_new_winning_trade(
        self, mock_list_trades, mock_console, tmp_path
    ):
        state = tmp_path
        checkpoint_path = state / "broker_checkpoint.json"
        trades_path = state / "trades.jsonl"
        trades_path.write_text("")

        new_trade = {
            "order_id": "order_123",
            "symbol": "AAPL",
            "pnl_pct": 2.0,
        }
        mock_list_trades.return_value = [new_trade]

        _reconcile_closed_trades(state, checkpoint_path)

        trades_content = trades_path.read_text()
        assert "order_123" in trades_content
        assert "AAPL" in trades_content

    @patch("hermes_trading.loop.console")
    @patch("hermes_trading.loop.broker.list_newly_closed_trades")
    def test_reconcile_duplicate_trade_ignored(
        self, mock_list_trades, mock_console, tmp_path
    ):
        state = tmp_path
        checkpoint_path = state / "broker_checkpoint.json"
        trades_path = state / "trades.jsonl"

        existing_trade = {
            "order_id": "order_123",
            "symbol": "AAPL",
            "pnl_pct": 2.0,
        }
        trades_path.write_text(json.dumps(existing_trade) + "\n")

        mock_list_trades.return_value = [existing_trade]

        _reconcile_closed_trades(state, checkpoint_path)

        lines = trades_path.read_text().strip().split("\n")
        assert len(lines) == 1
