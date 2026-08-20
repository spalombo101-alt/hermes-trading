import pytest
from hermes_trading.adapters.price import _rsi, _atr, _macd, _ema, _bollinger_bands


class TestRSI:
    def test_rsi_insufficient_data(self):
        closes = [100, 101, 102]
        rsi = _rsi(closes, period=14)
        assert rsi == 50.0

    def test_rsi_neutral_price(self):
        closes = [100.0] * 50
        rsi = _rsi(closes, period=14)
        assert 45.0 < rsi < 100.0

    def test_rsi_uptrend(self):
        closes = list(range(100, 120))
        rsi = _rsi(closes, period=14)
        assert rsi > 50.0

    def test_rsi_downtrend(self):
        closes = list(range(120, 100, -1))
        rsi = _rsi(closes, period=14)
        assert rsi < 50.0


class TestATR:
    def test_atr_insufficient_data(self):
        closes = [100, 101, 102]
        highs = [101, 102, 103]
        lows = [99, 100, 101]
        atr = _atr(highs, lows, closes, period=14)
        assert atr == 0.0

    def test_atr_volatile_market(self):
        closes = [100, 110, 95, 120, 80, 115]
        highs = [110, 115, 100, 125, 85, 120]
        lows = [95, 105, 90, 115, 75, 110]
        atr = _atr(highs, lows, closes, period=2)
        assert atr > 0

    def test_atr_calm_market(self):
        closes = [100.0] * 20
        highs = [100.1] * 20
        lows = [99.9] * 20
        atr = _atr(highs, lows, closes, period=5)
        assert atr < 1.0


class TestMACD:
    def test_macd_insufficient_data(self):
        closes = [100, 101, 102]
        macd, signal, histogram = _macd(closes)
        assert (macd, signal, histogram) == (0.0, 0.0, 0.0)

    def test_macd_returns_tuple(self):
        closes = list(range(100, 150))
        macd, signal, histogram = _macd(closes)
        assert isinstance(macd, float)
        assert isinstance(signal, float)
        assert isinstance(histogram, float)

    def test_macd_histogram_calculation(self):
        closes = list(range(100, 150))
        macd, signal, histogram = _macd(closes)
        assert abs(histogram - (macd - signal)) < 0.0001


class TestEMA:
    def test_ema_insufficient_data(self):
        data = [100, 101, 102]
        ema = _ema(data, period=5)
        assert ema == data

    def test_ema_returns_list(self):
        data = list(range(100, 150))
        ema = _ema(data, period=5)
        assert isinstance(ema, list)
        assert len(ema) > 0

    def test_ema_single_value(self):
        data = [100.0] * 20
        ema = _ema(data, period=5)
        for val in ema:
            assert abs(val - 100.0) < 0.01


class TestBollingerBands:
    def test_bb_insufficient_data(self):
        closes = [100, 101, 102]
        upper, middle, lower = _bollinger_bands(closes, period=20)
        assert upper == closes[-1]
        assert middle == closes[-1]
        assert lower == closes[-1]

    def test_bb_middle_is_sma(self):
        closes = [100, 101, 102, 103, 104]
        upper, middle, lower = _bollinger_bands(closes, period=5)
        expected_sma = sum(closes) / len(closes)
        assert abs(middle - expected_sma) < 0.01

    def test_bb_bands_order(self):
        closes = list(range(100, 150))
        upper, middle, lower = _bollinger_bands(closes)
        assert upper > middle > lower
