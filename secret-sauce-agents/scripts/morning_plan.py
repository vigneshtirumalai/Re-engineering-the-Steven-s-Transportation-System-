"""Decide which /morning steps run today, and record processed inbox files.

Usage:
  python scripts/morning_plan.py plan [--today YYYY-MM-DD]      -> JSON plan on stdout
  python scripts/morning_plan.py mark-done <client> <platform> <file>...

State lives in logs/last_run.json: {"<client>/<platform>": {"<file name>": <mtime>}}.
A settlement file is new if its name is not recorded or its mtime changed.
"""
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
AGENTS_DIR = paths.REPO_ROOT / ".claude" / "agents"
STATE_FILE = paths.LOGS_DIR / "last_run.json"
DATA_SUFFIXES = {".xlsx", ".xls", ".csv"}


def _load_state(state_file):
    return json.loads(state_file.read_text()) if state_file.exists() else {}


def _clients():
    return sorted(p.parent.name for p in paths.CLIENTS_DIR.glob("*/config.yaml"))


def _data_files(folder):
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in DATA_SUFFIXES)


def _agent_ready(name):
    return (AGENTS_DIR / f"{name}.md").exists()


def new_settlement_files(state, inbox_dir):
    found = {}
    for client in _clients():
        for platform in ("zomato", "swiggy"):
            seen = state.get(f"{client}/{platform}", {})
            new = [p for p in _data_files(inbox_dir / client / platform)
                   if seen.get(p.name) != p.stat().st_mtime]
            if new:
                found[f"{client}/{platform}"] = [str(p) for p in new]
    return found


def _next_month(today):
    return date(today.year + today.month // 12, today.month % 12 + 1, 1).strftime("%Y-%m")


def adbudget_step(today, inbox_dir, outputs_dir):
    clients = [c for c in _clients() if (paths.CLIENTS_DIR / c / "budget_rules.yaml").exists()]
    steps = []
    for client in clients:
        rules = yaml.safe_load((paths.CLIENTS_DIR / client / "budget_rules.yaml").read_text())
        draft_day = rules["scaling"]["draft_on_day"]
        budget_month = _next_month(today)
        step = {"step": "adbudget", "client": client, "budget_month": budget_month}
        if today.day < draft_day:
            steps.append({**step, "run": False, "reason": f"runs from day {draft_day} of the month"})
            continue
        if (outputs_dir / client / budget_month / "budget_draft.xlsx").exists():
            steps.append({**step, "run": False, "reason": "draft already written this month"})
            continue
        month_start = datetime(today.year, today.month, 1, tzinfo=IST).timestamp()
        missing = [f"inbox/{client}/{p}/ (exports for {today:%Y-%m})"
                   for p in rules["products"]
                   if not any(f.stat().st_mtime >= month_start
                              for f in _data_files(inbox_dir / client / p))]
        if missing:
            steps.append({**step, "run": False, "reason": "exports missing", "missing": missing})
        else:
            steps.append({**step, "run": _agent_ready("ad-budget"),
                          "reason": "ready" if _agent_ready("ad-budget") else "ad-budget agent missing"})
    return steps


def plan(today, inbox_dir=None, outputs_dir=None, state_file=STATE_FILE):
    inbox_dir = inbox_dir or paths.INBOX_DIR
    outputs_dir = outputs_dir or paths.OUTPUTS_DIR
    digest_ready = _agent_ready("client-digest")
    steps = [{"step": "digest", "client": "all", "run": digest_ready,
              "reason": "daily" if digest_ready else "client-digest agent not built yet (Prompt 2)"}]
    for key, files in new_settlement_files(_load_state(state_file), inbox_dir).items():
        client, platform = key.split("/")
        steps.append({"step": "recon", "client": client, "platform": platform,
                      "run": _agent_ready("payout-recon"), "files": files,
                      "reason": "new settlement files"})
    steps += adbudget_step(today, inbox_dir, outputs_dir)
    steps.append({"step": "score_predictions", "run": True, "reason": "daily"})
    return {"date": today.isoformat(), "inbox": str(inbox_dir), "steps": steps}


def mark_done(client, platform, files, state_file=STATE_FILE):
    state = _load_state(state_file)
    seen = state.setdefault(f"{client}/{platform}", {})
    for f in files:
        p = Path(f)
        seen[p.name] = p.stat().st_mtime
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--today", type=date.fromisoformat, default=datetime.now(IST).date())
    p_done = sub.add_parser("mark-done")
    p_done.add_argument("client")
    p_done.add_argument("platform")
    p_done.add_argument("files", nargs="+")
    args = parser.parse_args()
    if args.cmd == "plan":
        print(json.dumps(plan(args.today), indent=2))
    else:
        mark_done(args.client, args.platform, args.files)
