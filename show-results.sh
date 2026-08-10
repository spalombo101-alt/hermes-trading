#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
railway ssh 'cd /app && uv run python -m hermes_trading.friendly > /app/state/friendly-status.md && cat /app/state/friendly-status.md'
