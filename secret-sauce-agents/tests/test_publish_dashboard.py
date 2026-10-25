import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import publish_dashboard as pub  # noqa: E402

FAKE_CHROME = """#!/usr/bin/env bash
for a in "$@"; do case "$a" in --print-to-pdf=*) printf '%%PDF-fake' > "${a#--print-to-pdf=}";; esac; done
"""


def _source(tmp_path):
    src = tmp_path / "index.html"
    src.write_text("<html>dashboard</html>")
    return src


def _chrome(tmp_path, script=FAKE_CHROME):
    bin_ = tmp_path / "chrome"
    bin_.write_text(script)
    bin_.chmod(0o755)
    return str(bin_)


def test_skips_without_drive_target(tmp_path, monkeypatch):
    monkeypatch.delenv("SECRET_SAUCE_DASHBOARD_DIR", raising=False)
    monkeypatch.delenv("SECRET_SAUCE_INBOX", raising=False)
    assert pub.publish(date(2026, 10, 25), source=_source(tmp_path))[0].startswith("skipped")


def test_target_defaults_next_to_inbox(tmp_path, monkeypatch):
    monkeypatch.delenv("SECRET_SAUCE_DASHBOARD_DIR", raising=False)
    monkeypatch.setenv("SECRET_SAUCE_INBOX", str(tmp_path / "Secret Sauce Agents" / "inbox"))
    assert pub.target_dir() == tmp_path / "Secret Sauce Agents" / "dashboard"


def test_publishes_html_pdf_and_archive_in_place(tmp_path):
    dest = tmp_path / "drive"
    dest.mkdir()
    existing = dest / "control-room.pdf"
    existing.write_text("old")
    inode = existing.stat().st_ino
    notes = pub.publish(date(2026, 10, 25), source=_source(tmp_path), dest=dest, chrome=_chrome(tmp_path))
    assert (dest / "control-room.html").read_text() == "<html>dashboard</html>"
    assert existing.read_text() == "%PDF-fake" and existing.stat().st_ino == inode
    assert (dest / "archive" / "control-room-2026-10-25.pdf").exists()
    assert sorted(p.name for p in dest.iterdir()) == ["archive", "control-room.html", "control-room.pdf"]
    assert notes[-1].startswith("printed")


def test_html_still_copied_when_pdf_fails(tmp_path):
    dest = tmp_path / "drive"
    notes = pub.publish(date(2026, 10, 25), source=_source(tmp_path), dest=dest,
                        chrome=_chrome(tmp_path, "#!/usr/bin/env bash\nexit 1\n"))
    assert (dest / "control-room.html").exists() and not (dest / "control-room.pdf").exists()
    assert notes[-1].startswith("no PDF")


def test_archive_keeps_90_days(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    for day in ("2026-07-26", "2026-07-27", "2026-10-24"):
        (archive / f"control-room-{day}.pdf").write_text("x")
    assert pub.prune_archive(archive, date(2026, 10, 25)) == 1
    assert sorted(p.name for p in archive.iterdir()) == ["control-room-2026-07-27.pdf", "control-room-2026-10-24.pdf"]
