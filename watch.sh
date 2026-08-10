#!/bin/bash
# Brain watcher: every 30 min, snapshot worker trades + strategy, flag reflection triggers.
cd "$HOME/hermes-trading" || exit 1
mkdir -p state/history .watch
MARK_FILE=.watch/last_reflection_count
[ -f "$MARK_FILE" ] || echo 0 > "$MARK_FILE"

while true; do
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  railway ssh 'cat /app/state/trades.jsonl' 2>/dev/null | grep '^{' > .watch/trades.remote.jsonl
  railway ssh 'cat /app/state/strategy.yaml' 2>/dev/null > .watch/strategy.remote.yaml
  N=$(wc -l < .watch/trades.remote.jsonl | tr -d ' ')
  LAST=$(cat "$MARK_FILE")
  NEW=$((N - LAST))
  echo "$TS closed_trades=$N since_last_reflection=$NEW" >> .watch/watch.log
  if [ "$NEW" -ge 5 ]; then
    echo "$TS REFLECTION_DUE total=$N new=$NEW" >> .watch/watch.log
    touch .watch/REFLECTION_DUE
  fi
  sleep 1800
done
