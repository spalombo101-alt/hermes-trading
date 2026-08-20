# Trading Bot Dashboard

View your bot's performance in real-time with easy-to-read dashboards.

## CLI Dashboard (Terminal)

Watch your bot's performance live in the terminal with auto-refresh:

```bash
uv run python -m hermes_trading.cli_dashboard --watch
```

Shows:
- Current price & RSI
- Total P&L and win rate
- Strategy settings
- Last 8 trades with entry/exit/P&L

Updates every 5 seconds.

## Web Dashboard (Browser)

Generate an HTML dashboard that auto-refreshes:

```bash
uv run python -m hermes_trading.dashboard
```

This creates `dashboard-live.html` in the project root. Open it in your browser:

```bash
open dashboard-live.html
```

The dashboard auto-refreshes every 60 seconds and shows:
- Current price and market conditions
- Total performance metrics
- Win rate and trade statistics
- Recent trades (last 10)
- Strategy configuration
- System status

## Auto-Update During Trading

The dashboard is automatically updated by the bot while it runs. The bot's main loop calls the dashboard update after each cycle.

## What Each Dashboard Shows

### Price Card
- Current price of the selected symbol
- Current RSI value
- Updated in real-time

### P&L Card
- Total profit/loss percentage
- Number of closed trades
- Color-coded (green = profit, red = loss)

### Win Rate Card
- Win percentage
- Number of wins vs losses
- Running ratio of successful trades

### Strategy Card
- Current strategy version
- Entry threshold (RSI level)
- Stop loss percentage
- Target performance goals

### Status Card
- Price feed connection
- Broker connection status
- Trading engine status
- Total trades tracked

### Recent Trades
- Timestamp of each trade
- Symbol traded
- Entry and exit prices
- P&L for each trade (color-coded)

## Integration with Bot Loop

The dashboard is automatically updated by the trading bot. When the bot runs:

```bash
uv run python -m hermes_trading.run
```

The `dashboard-live.html` file is updated after each trading cycle, so you can monitor it in real-time.

## Monitoring While Deployed

When deployed to Railway or another cloud service, you can:

1. **Pull dashboard locally:**
   ```bash
   railway ssh 'cat /app/dashboard-live.html' > remote-dashboard.html
   open remote-dashboard.html
   ```

2. **View latest metrics:**
   ```bash
   railway ssh 'cat /app/state/heartbeat.json'
   railway ssh 'tail -5 /app/state/trades.jsonl'
   ```

## Customization

Both dashboards read from the same state files:
- `state/heartbeat.json` - Current price and RSI
- `state/trades.jsonl` - All completed trades
- `state/strategy.yaml` - Current strategy settings
- `state/goal.yaml` - Performance goals

You can modify colors and layout in:
- `hermes_trading/dashboard.py` - HTML styling
- `hermes_trading/cli_dashboard.py` - Terminal styling (Rich library)
