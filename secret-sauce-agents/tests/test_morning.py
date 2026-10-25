import csv
import os
import subprocess
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import log_review  # noqa: E402
from morning_plan import mark_done, plan  # noqa: E402
from score_predictions import evaluate, score  # noqa: E402

NOW = datetime.now()


def _steps(result, name):
    return [s for s in result["steps"] if s["step"] == name]


@pytest.fixture
def dirs(tmp_path):
    inbox, outputs = tmp_path / "inbox", tmp_path / "outputs"
    for client in ("tempt", "tbs"):
        for platform in ("zomato", "swiggy"):
            (inbox / client / platform).mkdir(parents=True)
    return inbox, outputs, tmp_path / "last_run.json"


def test_digest_skipped_until_agent_exists(dirs):
    inbox, outputs, state = dirs
    [digest] = _steps(plan(date(2026, 10, 25), inbox, outputs, state), "digest")
    assert digest["run"] is False and "Prompt 2" in digest["reason"]


def test_recon_runs_on_new_files_until_marked_done(dirs):
    inbox, outputs, state = dirs
    f = inbox / "tempt" / "zomato" / "annexure_2026-10-12.xlsx"
    f.write_text("x")
    (inbox / "tempt" / "zomato" / "notes.txt").write_text("ignored")
    [recon] = _steps(plan(date(2026, 10, 25), inbox, outputs, state), "recon")
    assert (recon["client"], recon["platform"], recon["run"]) == ("tempt", "zomato", True)
    assert recon["files"] == [str(f)]

    mark_done("tempt", "zomato", [str(f)], state_file=state)
    assert _steps(plan(date(2026, 10, 25), inbox, outputs, state), "recon") == []

    os.utime(f, (f.stat().st_atime, f.stat().st_mtime + 60))  # re-downloaded file
    assert len(_steps(plan(date(2026, 10, 25), inbox, outputs, state), "recon")) == 1


def test_adbudget_waits_for_day_27_and_exports(dirs):
    inbox, outputs, state = dirs
    [early] = _steps(plan(date(NOW.year, NOW.month, 26), inbox, outputs, state), "adbudget")
    assert early["run"] is False and "day 27" in early["reason"]

    day27 = date(NOW.year, NOW.month, 27)
    [missing] = _steps(plan(day27, inbox, outputs, state), "adbudget")
    assert missing["run"] is False and len(missing["missing"]) == 2

    (inbox / "tbs" / "zomato" / "ads.csv").write_text("x")
    (inbox / "tbs" / "swiggy" / "cpc.xlsx").write_text("x")
    [ready] = _steps(plan(day27, inbox, outputs, state), "adbudget")
    assert ready["run"] is True

    draft = outputs / "tbs" / ready["budget_month"] / "budget_draft.xlsx"
    draft.parent.mkdir(parents=True)
    draft.write_text("x")
    [done] = _steps(plan(day27, inbox, outputs, state), "adbudget")
    assert done["run"] is False and "already" in done["reason"]


def test_hit_rule_evaluation_is_safe():
    names = {"orders_7d_avg": Decimal("115"), "baseline": Decimal("100")}
    assert evaluate("orders_7d_avg >= baseline * 1.10", names) is True
    assert evaluate("orders_7d_avg < baseline", names) is False
    for bad in ("__import__('os').system('x')", "orders_7d_avg", "unknown > 1", "1 >"):
        with pytest.raises(ValueError):
            evaluate(bad, names)


def _pred(**kw):
    base = {"prediction_id": "p1", "date": "2026-09-01", "workflow": "adbudget",
            "client": "tbs", "outlet": "22734640", "platform": "zomato",
            "metric": "orders_7d_avg", "baseline_value": "100", "direction": "up",
            "magnitude": "0.10", "horizon_days": "30",
            "hit_rule": "orders_7d_avg >= baseline * 1.10",
            "outcome_value": "", "scored": "", "scored_date": ""}
    return {**base, **kw}


def _metric(day, value):
    return {"date": day, "client": "tbs", "outlet": "22734640", "platform": "zomato",
            "metric": "orders_7d_avg", "value": value}


def test_scoring_hit_miss_unclear_and_pending():
    preds = [
        _pred(prediction_id="hit"),
        _pred(prediction_id="miss", hit_rule="orders_7d_avg >= baseline * 1.50"),
        _pred(prediction_id="unclear", hit_rule="orders goes up"),
        _pred(prediction_id="no_data", outlet="22566498"),
        _pred(prediction_id="not_due", date="2026-10-20"),
    ]
    metrics = [_metric("2026-09-30", "90"), _metric("2026-10-02", "120")]
    assert score(preds, metrics, date(2026, 10, 25)) == 3
    by_id = {p["prediction_id"]: p for p in preds}
    assert by_id["hit"]["scored"] == "hit" and by_id["hit"]["outcome_value"] == "120"
    assert by_id["miss"]["scored"] == "miss"
    assert by_id["unclear"]["scored"] == "unclear"
    assert by_id["no_data"]["scored"] == "" and by_id["not_due"]["scored"] == ""


def test_log_review_appends_and_validates(tmp_path):
    log = tmp_path / "review_log.csv"
    log.write_text("date,workflow,client,output_path,edits_numbers,edits_text,minutes_spent,notes\n")
    log_review.main(["recon", "tempt", "0", "1", "12", "fixed summary wording"], log=log)
    rows = list(csv.DictReader(log.open()))
    assert rows[0]["edits_numbers"] == "0" and rows[0]["minutes_spent"] == "12"
    with pytest.raises(SystemExit):
        log_review.main(["recon", "tempt", "4", "0", "5"], log=log)


def _run_morning(tmp_path, claude_script):
    fake = tmp_path / "fake_claude"
    fake.write_text("#!/usr/bin/env bash\n" + claude_script)
    fake.chmod(0o755)
    env = {**os.environ, "CLAUDE_BIN": str(fake), "BRIEF_DIR": str(tmp_path / "brief"),
           "LOG_DIR": str(tmp_path / "runs"), "MORNING_SKIP_DASHBOARD": "1"}
    result = subprocess.run(["bash", str(ROOT / "scripts" / "run_morning.sh")], env=env,
                            capture_output=True, text=True)
    briefs = list((tmp_path / "brief").glob("*.md"))
    return result.returncode, briefs[0].read_text() if briefs else None


def test_run_morning_writes_failed_brief_when_claude_fails(tmp_path):
    rc, brief = _run_morning(tmp_path, 'echo "auth expired"; exit 3\n')
    assert rc == 3
    assert "FAILED" in brief and "exit code 3" in brief and "auth expired" in brief


def test_run_morning_fails_when_no_brief_written(tmp_path):
    rc, brief = _run_morning(tmp_path, "exit 0\n")
    assert rc == 1 and "FAILED" in brief


def test_run_morning_keeps_agent_brief_on_success(tmp_path):
    rc, brief = _run_morning(
        tmp_path, 'echo "# Morning brief" > "$BRIEF_DIR/$(TZ=Asia/Kolkata date +%F).md"\n')
    assert rc == 0 and brief == "# Morning brief\n"
