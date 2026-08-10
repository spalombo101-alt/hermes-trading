from __future__ import annotations
import argparse, json, shutil, subprocess, time
from pathlib import Path
import yaml
from .score import score
from .friendly import write_summary

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"

DEFAULT_GOAL = '''asset: "AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,JPM"
target_return_30d: 0.05
max_drawdown: 0.05
min_sharpe: 1.2
failure_below: -0.04
reflection_every: 5
one_variable_only: true
'''

DEFAULT_STRATEGY = '''version: "01"
entry:
  indicator: rsi
  threshold: 30
  direction: long
stop_loss_pct: 2.0
position_size_r: 0.5
'''

def ensure_state():
    (STATE / "history").mkdir(parents=True, exist_ok=True)
    defaults = {"goal.yaml": DEFAULT_GOAL, "strategy.yaml": DEFAULT_STRATEGY, "trades.jsonl": "", "hypotheses.jsonl": ""}
    for name, content in defaults.items():
        path = STATE / name
        if not path.exists():
            path.write_text(content)

def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def bump_version(strategy: dict) -> tuple[dict, str, str]:
    old = str(strategy.get("version", "01")).zfill(2)
    new = str(int(old) + 1).zfill(2)
    strategy["version"] = new
    return strategy, old, new

def metrics(trades: list[dict], goal: dict) -> dict:
    realised = sum(float(t.get("pnl_pct", 0)) for t in trades) / 100.0
    equity = 1.0; peak = 1.0; dd = 0.0
    for t in trades:
        equity *= 1 + float(t.get("pnl_pct", 0)) / 100.0
        peak = max(peak, equity); dd = max(dd, (peak - equity) / peak)
    return {"realised_return": realised, "drawdown": dd, "score": score(trades, goal)}

def save_change(strategy: dict, old_version: str, hypothesis: dict):
    hist = STATE / "history" / f"v{old_version}.yaml"
    shutil.copy2(STATE / "strategy.yaml", hist)
    (STATE / "strategy.yaml").write_text(yaml.safe_dump(strategy, sort_keys=False))
    with (STATE / "hypotheses.jsonl").open("a") as f:
        f.write(json.dumps(hypothesis, sort_keys=True) + "\n")
    write_summary(STATE)

def fallback():
    goal = yaml.safe_load((STATE / "goal.yaml").read_text())
    strategy = yaml.safe_load((STATE / "strategy.yaml").read_text())
    trades = load_jsonl(STATE / "trades.jsonl")
    m = metrics(trades, goal)
    changed = None
    prior = None
    if m["drawdown"] > float(goal["max_drawdown"]):
        prior = strategy["stop_loss_pct"]
        strategy["stop_loss_pct"] = round(max(0.2, float(prior) - 0.2), 2)
        changed = "stop_loss_pct"
        reason = "drawdown exceeded max, tightening stop loss by 0.2"
    else:
        prior = strategy["entry"]["threshold"]
        strategy["entry"]["threshold"] = int(prior) + 2 if m["realised_return"] < float(goal["target_return_30d"]) else max(5, int(prior) - 2)
        changed = "entry.threshold"
        reason = "realised return below target, loosening entry threshold by 2" if m["realised_return"] < float(goal["target_return_30d"]) else "target met, tightening entry threshold by 2"
    strategy, old, new = bump_version(strategy)
    hypothesis = {"ts": int(time.time()), "mode": "fallback", "from_version": old, "to_version": new, "changed": changed, "prior": prior, "new": strategy["entry"]["threshold"] if changed == "entry.threshold" else strategy["stop_loss_pct"], "reason": reason, "metrics": m}
    save_change(strategy, old, hypothesis)
    print(json.dumps(hypothesis, indent=2))

def hermes():
    goal = yaml.safe_load((STATE / "goal.yaml").read_text())
    strategy = yaml.safe_load((STATE / "strategy.yaml").read_text())
    trades = load_jsonl(STATE / "trades.jsonl")[-25:]
    prompt = f"""You improve one YAML trading strategy. Return JSON only with keys variable, new_value, reason. Change exactly one variable.\nGoal: {json.dumps(goal)}\nCurrent strategy: {yaml.safe_dump(strategy)}\nLatest trades: {json.dumps(trades)}"""
    result = subprocess.run(["hermes", "--prompt", prompt], text=True, capture_output=True, check=True, timeout=300)
    proposal = json.loads(result.stdout.strip().splitlines()[-1])
    variable = proposal["variable"]
    if variable == "entry.threshold":
        prior = strategy["entry"]["threshold"]; strategy["entry"]["threshold"] = proposal["new_value"]
    elif variable == "stop_loss_pct":
        prior = strategy["stop_loss_pct"]; strategy["stop_loss_pct"] = proposal["new_value"]
    elif variable == "position_size_r":
        prior = strategy["position_size_r"]; strategy["position_size_r"] = proposal["new_value"]
    else:
        raise ValueError(f"unsupported one-variable change: {variable}")
    strategy, old, new = bump_version(strategy)
    hypothesis = {"ts": int(time.time()), "mode": "hermes", "from_version": old, "to_version": new, "changed": variable, "prior": prior, "new": proposal["new_value"], "reason": proposal.get("reason", ""), "score": score(trades, goal)}
    save_change(strategy, old, hypothesis)
    print(json.dumps(hypothesis, indent=2))

def main():
    ensure_state()
    parser = argparse.ArgumentParser()
    parser.add_argument("--fallback", action="store_true")
    parser.add_argument("--hermes", action="store_true")
    args = parser.parse_args()
    if args.hermes:
        hermes()
    else:
        fallback()

if __name__ == "__main__":
    main()
