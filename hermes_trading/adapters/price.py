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
            hist = ticker.history(period="60d")
            if hist.empty:
                data[symbol] = {"price": None, "rsi": 50.0, "error": "No data"}
                continue
            closes = hist["Close"].tolist()
            latest_price = closes[-1]
            rsi = _rsi(closes)
            data[symbol] = {"price": round(latest_price, 2), "rsi": round(rsi, 2)}
        except Exception as e:
            data[symbol] = {"price": None, "rsi": 50.0, "error": str(e)}
    
    best_symbol = None
    best_rsi = 100.0
    for symbol, info in data.items():
        if info.get("price") and info["rsi"] < best_rsi:
            best_rsi = info["rsi"]
            best_symbol = symbol
    
    return {
        "schema_version": "1.0",
        "asset": asset,
        "timestamp": int(__import__("time").time()),
        "prices": data,
        "best_match": {"symbol": best_symbol or "AAPL", "rsi": best_rsi},
    }
