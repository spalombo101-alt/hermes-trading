import pytest
from unittest.mock import patch, MagicMock, Mock
from hermes_trading.adapters.broker import (
    _is_paper_mode,
    client,
    account,
    get_open_position,
    get_all_positions,
    has_open_position,
    submit_bracket_order,
    list_newly_closed_trades,
    BrokerError,
)


class TestPaperMode:
    def test_paper_mode_default(self):
        with patch.dict("os.environ", {}, clear=True):
            assert _is_paper_mode() is True

    def test_paper_mode_explicit_paper(self):
        with patch.dict("os.environ", {"HERMES_TRADING_MODE": "paper"}):
            assert _is_paper_mode() is True

    def test_live_mode_without_acceptance(self):
        with patch.dict("os.environ", {"HERMES_TRADING_MODE": "live"}):
            assert _is_paper_mode() is True

    def test_live_mode_with_acceptance(self):
        with patch.dict(
            "os.environ",
            {
                "HERMES_TRADING_MODE": "live",
                "HERMES_TRADING_I_ACCEPT_RISK": "true",
            },
        ):
            assert _is_paper_mode() is False


class TestClientInitialization:
    def test_client_missing_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("hermes_trading.adapters.broker._client", None):
                with pytest.raises(BrokerError):
                    client()

    def test_client_missing_secret(self):
        with patch.dict("os.environ", {"ALPACA_API_KEY": "test_key"}, clear=True):
            with patch("hermes_trading.adapters.broker._client", None):
                with pytest.raises(BrokerError):
                    client()


class TestAccount:
    @patch("hermes_trading.adapters.broker.client")
    def test_account_returns_dict(self, mock_client_func):
        mock_acct = MagicMock()
        mock_acct.equity = 100000.0
        mock_acct.cash = 50000.0
        mock_acct.buying_power = 50000.0

        mock_client_instance = MagicMock()
        mock_client_instance.get_account.return_value = mock_acct
        mock_client_func.return_value = mock_client_instance

        result = account()
        assert isinstance(result, dict)
        assert "equity" in result
        assert "cash" in result
        assert "buying_power" in result
        assert result["equity"] == 100000.0


class TestGetOpenPosition:
    @patch("hermes_trading.adapters.broker.client")
    def test_get_position_exists(self, mock_client_func):
        mock_pos = MagicMock()
        mock_pos.symbol = "AAPL"
        mock_pos.qty = 100.0
        mock_pos.avg_entry_price = 150.0
        mock_pos.unrealized_plpc = 0.05

        mock_client_instance = MagicMock()
        mock_client_instance.get_open_position.return_value = mock_pos
        mock_client_func.return_value = mock_client_instance

        result = get_open_position("AAPL")
        assert result is not None
        assert result["symbol"] == "AAPL"
        assert result["qty"] == 100.0

    @patch("hermes_trading.adapters.broker.client")
    def test_get_position_not_found(self, mock_client_func):
        mock_client_instance = MagicMock()
        mock_client_instance.get_open_position.side_effect = Exception(
            "Position not found"
        )
        mock_client_func.return_value = mock_client_instance

        result = get_open_position("AAPL")
        assert result is None


class TestGetAllPositions:
    @patch("hermes_trading.adapters.broker.client")
    def test_get_all_positions_empty(self, mock_client_func):
        mock_client_instance = MagicMock()
        mock_client_instance.get_all_positions.return_value = []
        mock_client_func.return_value = mock_client_instance

        result = get_all_positions()
        assert result == []

    @patch("hermes_trading.adapters.broker.client")
    def test_get_all_positions_multiple(self, mock_client_func):
        mock_pos1 = MagicMock()
        mock_pos1.symbol = "AAPL"
        mock_pos1.qty = 100.0
        mock_pos1.avg_entry_price = 150.0

        mock_pos2 = MagicMock()
        mock_pos2.symbol = "MSFT"
        mock_pos2.qty = 50.0
        mock_pos2.avg_entry_price = 300.0

        mock_client_instance = MagicMock()
        mock_client_instance.get_all_positions.return_value = [
            mock_pos1,
            mock_pos2,
        ]
        mock_client_func.return_value = mock_client_instance

        result = get_all_positions()
        assert len(result) == 2
        assert result[0]["symbol"] == "AAPL"
        assert result[1]["symbol"] == "MSFT"


class TestHasOpenPosition:
    @patch("hermes_trading.adapters.broker.client")
    def test_has_open_position_true(self, mock_client_func):
        mock_pos = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.get_all_positions.return_value = [mock_pos]
        mock_client_func.return_value = mock_client_instance

        result = has_open_position()
        assert result is True

    @patch("hermes_trading.adapters.broker.client")
    def test_has_open_position_false(self, mock_client_func):
        mock_client_instance = MagicMock()
        mock_client_instance.get_all_positions.return_value = []
        mock_client_func.return_value = mock_client_instance

        result = has_open_position()
        assert result is False


class TestSubmitBracketOrder:
    @patch("hermes_trading.adapters.broker.client")
    def test_submit_order_success(self, mock_client_func):
        mock_order = MagicMock()
        mock_order.id = "order_123"
        mock_order.client_order_id = "hermes-v01-123456"

        mock_client_instance = MagicMock()
        mock_client_instance.submit_order.return_value = mock_order
        mock_client_func.return_value = mock_client_instance

        result = submit_bracket_order("AAPL", 100, 155.0, 147.0, "01")
        assert result["id"] == "order_123"
        assert result["symbol"] == "AAPL"
        assert result["qty"] == 100
