"""Score predictions whose horizon has passed.

Usage: python scripts/score_predictions.py [--today YYYY-MM-DD]

Outcomes come from logs/metrics.csv (date, client, outlet, platform, metric, value), which
each workflow appends its computed metrics to. For a prediction made on D with horizon H,
the outcome is the first metric value dated on or after D+H, within GRACE_DAYS.

hit_rule is a small expression over the metric name (or `value`) and `baseline`, e.g.
"orders_7d_avg >= baseline * 1.10". It is parsed, never eval'd.
- No outcome yet: row left blank, retried next run.
- Outcome found but rule cannot be evaluated: scored "unclear".
"""
import argparse
import ast
import csv
import operator
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from recon_schema import to_decimal  # noqa: E402

PREDICTIONS = paths.LOGS_DIR / "predictions.csv"
METRICS = paths.LOGS_DIR / "metrics.csv"
METRIC_COLUMNS = ["date", "client", "outlet", "platform", "metric", "value"]
GRACE_DAYS = 7

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.Lt: operator.lt, ast.LtE: operator.le, ast.Eq: operator.eq, ast.NotEq: operator.ne,
}


def evaluate(rule, names):
    """Evaluate a hit_rule with Decimal arithmetic. Raises ValueError on anything else."""
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.BoolOp):
            values = [ev(v) for v in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Compare):
            left = ev(node.left)
            for op, comp in zip(node.ops, node.comparators):
                right = ev(comp)
                if type(op) not in _OPS or not _OPS[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return Decimal(str(node.value))
        if isinstance(node, ast.Name) and node.id in names:
            return names[node.id]
        raise ValueError(f"unsupported in hit_rule: {ast.dump(node)}")

    try:
        result = ev(ast.parse(rule, mode="eval"))
    except SyntaxError as exc:
        raise ValueError(str(exc)) from exc
    if not isinstance(result, bool):
        raise ValueError("hit_rule must be a comparison")
    return result


def find_outcome(metrics, pred):
    due = date.fromisoformat(pred["date"]) + timedelta(days=int(pred["horizon_days"]))
    candidates = sorted(
        (m for m in metrics
         if (m["client"], m["outlet"], m["platform"], m["metric"]) ==
            (pred["client"], pred["outlet"], pred["platform"], pred["metric"])
         and due <= date.fromisoformat(m["date"]) <= due + timedelta(days=GRACE_DAYS)),
        key=lambda m: m["date"])
    return to_decimal(candidates[0]["value"]) if candidates else None


def score(predictions, metrics, today):
    scored = 0
    for pred in predictions:
        if pred.get("scored"):
            continue
        due = date.fromisoformat(pred["date"]) + timedelta(days=int(pred["horizon_days"]))
        if due > today:
            continue
        outcome = find_outcome(metrics, pred)
        if outcome is None:
            continue
        pred["outcome_value"] = str(outcome)
        pred["scored_date"] = today.isoformat()
        try:
            names = {pred["metric"]: outcome, "value": outcome,
                     "baseline": to_decimal(pred["baseline_value"])}
            pred["scored"] = "hit" if evaluate(pred["hit_rule"], names) else "miss"
        except ValueError:
            pred["scored"] = "unclear"
        scored += 1
    return scored


def _read(path):
    if not path.exists():
        return [], None
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", type=date.fromisoformat,
                        default=datetime.now(ZoneInfo("Asia/Kolkata")).date())
    args = parser.parse_args()
    predictions, fields = _read(PREDICTIONS)
    metrics, _ = _read(METRICS)
    n = score(predictions, metrics, args.today)
    with open(PREDICTIONS, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(predictions)
    print(f"scored {n} prediction(s)")
