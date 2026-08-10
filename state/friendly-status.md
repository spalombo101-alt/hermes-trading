# Trading Agent Status — Plain English

Updated: 2026-08-08 19:03 UTC

## Big Picture

This is a paper-trading bot watching **BTC/USDT**. Paper trading means it is practicing with fake trades, not risking real money.
The goal is to learn a strategy that could make about **5.0% over 30 days** while avoiding losses worse than **5.0%**.

## What The Bot Is Doing Right Now

- Latest price seen: not available yet
- Market read: not available yet
- Current paper position: **none**
- Current strategy: Version 02: the bot looks for moments when the market seems weak or oversold and may buy if its simple momentum gauge falls to 32 or below. It uses a 2.0% paper stop-loss and a small test position size of 0.5R.

## Results So Far

- Closed paper trades: **0**
- Wins / losses: **0 wins**, **0 losses**
- Net paper result: **flat 0.000%** across all closed trades
- Next strategy review: **5 more closed trade(s)**

## What Hermes Changed

Hermes last changed **entry.threshold** from **30** to **32**.

Plain-English reason: realised return below target, loosening entry threshold by 2.

That means Hermes made one small adjustment, then kept everything else the same so we can see whether that one change helps.

## How To Read This

- A tiny gain or loss is normal right now; the bot is still learning.
- The important thing is whether each version improves over multiple trades.
- Because this is paper mode, nothing here is financial advice and no real money is being traded.
