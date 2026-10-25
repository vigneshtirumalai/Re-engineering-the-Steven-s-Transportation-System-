import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import build_dashboard as dash  # noqa: E402
from build_recon_workbook import build as build_recon  # noqa: E402
from test_recon import _outlet  # noqa: E402

HEADER = {
    "predictions.csv": "prediction_id,date,workflow,client,outlet,platform,metric,baseline_value,"
                       "direction,magnitude,horizon_days,hit_rule,outcome_value,scored,scored_date\n",
    "review_log.csv": "date,workflow,client,output_path,edits_numbers,edits_text,minutes_spent,notes\n",
}


def _dirs(tmp_path):
    out, logs, inbox = tmp_path / "outputs", tmp_path / "logs", tmp_path / "inbox"
    for p in (out / "brief", logs, inbox):
        p.mkdir(parents=True)
    for name, header in HEADER.items():
        (logs / name).write_text(header)
    return {"outputs_dir": out, "logs_dir": logs, "inbox_dir": inbox}


def test_empty_state_renders(tmp_path):
    dirs = _dirs(tmp_path)
    page = dash.build(date(2026, 10, 25), tmp_path / "index.html", **dirs).read_text()
    assert "No recon weeks yet" in page and "No brief yet" in page
    assert "Not built (Prompt 2)" in page


def test_outputs_flow_into_page(tmp_path):
    dirs = _dirs(tmp_path)
    out, logs = dirs["outputs_dir"], dirs["logs_dir"]
    wk = out / "tempt" / "2026-10-12"
    build_recon(_outlet("21306274", payout="747.50"), wk / "recon.xlsx")
    (wk / "checker.md").write_text("FAIL\n21306274 net_settlement off by 12.50\n")
    dg = out / "tbs" / "digests"
    dg.mkdir(parents=True)
    (dg / "2026-10-25_whatsapp.txt").write_text("Orders steady <b>\n")
    (dg / "2026-10-25_verify.txt").write_text("rating (llm_extracted)")
    (out / "brief" / "2026-10-25.md").write_text(
        "# Morning brief: FAILED\n\n## Decide today\n- Approve Potheri push\n\n## Missing\n- x\n")
    with open(logs / "review_log.csv", "a") as f:
        f.write("2026-10-07,recon,tempt,,0,1,12,\n2026-10-14,recon,tempt,,0,0,10,\n"
                "2026-10-21,recon,tempt,,0,1,14,\n2026-10-21,digest,tbs,,1,0,8,\n")

    data = dash.collect(date(2026, 10, 25), **dirs)
    [recon] = data["recon"]
    assert recon["verdict"] == "FAIL"
    assert recon["rates"][0]["Cash Keep Rate"] == float(Decimal("747.50") / 1000)
    assert {a["name"]: a["status"] for a in data["agents"]}["Morning run"] == "failed"
    assert data["trust"]["recon"]["streak"] == 3
    assert data["trust"]["digest"]["streak"] == 0  # edits on numbers breaks the bar

    page = dash.render(data)
    assert "Checker FAIL" in page and "74.8%" in page
    assert "Approve Potheri push" in page.split("Agents")[0]  # decisions sit at the top
    assert "Orders steady &lt;b&gt;" in page  # drafts are escaped
    assert "Verify first" in page


def test_trust_streak_breaks_on_gap_week(tmp_path):
    logs = tmp_path
    (logs / "review_log.csv").write_text(HEADER["review_log.csv"]
                                         + "2026-09-30,recon,tempt,,0,0,10,\n2026-10-21,recon,tempt,,0,0,10,\n")
    assert dash.trust_streaks(logs)["recon"]["streak"] == 1


def test_decide_today_extracts_bullets():
    text = "# Brief\n## Status\n- digest: OK\n## Decide today\n- One\n- Two\n## Missing\n- x\n"
    assert dash.decide_today(text) == ["One", "Two"]
