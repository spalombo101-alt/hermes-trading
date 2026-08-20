import os
import asyncio
import yfinance as yf

DEFAULT_STOCKS = "AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,JPM"


def _rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) <= period:
        return 50.0
    gains, losses = [], []
    for prev, cur in zip(closes[-period - 1 : -1], closes[-period:]):
        diff = cur - prev
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period if gains else 0.001
    avg_loss = sum(losses) / period if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
    if len(closes) < period:
        return 0.0
    trs = []
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i - 1])
        low_close = abs(lows[i] - closes[i - 1])
        tr = max(high_low, high_close, low_close)
        trs.append(tr)
    atr = sum(trs[-period:]) / period
    return atr


def _macd(closes: list[float]) -> tuple[float, float, float]:
    if len(closes) < 26:
        return 0.0, 0.0, 0.0
    ema_12 = _ema(closes, 12)
    ema_26 = _ema(closes, 26)
    # Both are lists; take the last values to match length, then compute MACD line
    macd_line = [e12 - e26 for e12, e26 in zip(ema_12, ema_26)]
    macd = macd_line[-1]
    if len(macd_line) >= 9:
        signal_line = _ema(macd_line, 9)
        signal = signal_line[-1]
    else:
        signal = macd
    histogram = macd - signal
    return macd, signal, histogram


def _ema(data: list[float], period: int) -> list[float]:
    if len(data) < period:
        return data
    multiplier = 2.0 / (period + 1)
    ema_list = [sum(data[:period]) / period]
    for price in data[period:]:
        ema_list.append((price * multiplier) + (ema_list[-1] * (1 - multiplier)))
    return ema_list


def _bollinger_bands(closes: list[float], period: int = 20, std_dev: float = 2.0) -> tuple[float, float, float]:
    if len(closes) < period:
        return closes[-1], closes[-1], closes[-1]
    recent = closes[-period:]
    sma = sum(recent) / period
    variance = sum((x - sma) ** 2 for x in recent) / period
    std = variance ** 0.5
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower


async def fetch(asset: str = None, open_position_symbol: str = None) -> dict:
    if asset is None:
        asset = DEFAULT_STOCKS
    if open_position_symbol:
        symbols = [open_position_symbol]
    else:
        symbols = [s.strip() for s in asset.split(",")]

    data = {}
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="90d")
            if hist.empty:
                data[symbol] = {"price": None, "rsi": 50.0, "error": "No data"}
                continue
            closes = hist["Close"].tolist()
            highs = hist["High"].tolist()
            lows = hist["Low"].tolist()
            latest_price = closes[-1]
            rsi = _rsi(closes)
            atr = _atr(highs, lows, closes)
            macd, signal, histogram = _macd(closes)
            upper_bb, middle_bb, lower_bb = _bollinger_bands(closes)

            data[symbol] = {
                "price": round(latest_price, 2),
                "rsi": round(rsi, 2),
                "atr": round(atr, 2),
                "macd": round(macd, 4),
                "signal": round(signal, 4),
                "histogram": round(histogram, 4),
                "bb_upper": round(upper_bb, 2),
                "bb_middle": round(middle_bb, 2),
                "bb_lower": round(lower_bb, 2),
            }
        except Exception as e:
            data[symbol] = {"price": None, "rsi": 50.0, "atr": 0.0, "error": str(e)}

    best_symbol = None
    best_score = -999.0
    for symbol, info in data.items():
        if not info.get("price"):
            continue
        rsi = info.get("rsi", 50.0)
        histogram = info.get("histogram", 0.0)
        score = (50.0 - rsi) + (10.0 if histogram <= 1.0 else -5.0)
        if score > best_score:
            best_score = score
            best_symbol = symbol

    return {
        "schema_version": "1.0",
        "asset": asset,
        "timestamp": int(__import__("time").time()),
        "prices": data,
        "best_match": {"symbol": best_symbol or "AAPL", "score": best_score},
    }
