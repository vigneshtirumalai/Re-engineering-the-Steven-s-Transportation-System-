"""Copy the dashboard into the Drive-synced folder, as HTML and as a phone-readable PDF.

Usage: python scripts/publish_dashboard.py [--today YYYY-MM-DD]

Target: $SECRET_SAUCE_DASHBOARD_DIR, else "<parent of $SECRET_SAUCE_INBOX>/dashboard"
(the Drive folder "Secret Sauce Agents/dashboard"). With neither set, nothing is published.
Google Drive for desktop uploads the files; overwriting control-room.pdf keeps its Drive
link, so a bookmark on the phone always opens the latest. Dated PDFs go to archive/
(kept for ARCHIVE_DAYS).

The PDF is printed with headless Chrome/Chromium ($CHROME_BIN, else the usual install
paths). Without a browser, only the HTML is copied and the reason is printed.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]
ARCHIVE_DAYS = 90


def target_dir():
    explicit = os.environ.get("SECRET_SAUCE_DASHBOARD_DIR")
    if explicit:
        return Path(explicit).expanduser()
    inbox = os.environ.get("SECRET_SAUCE_INBOX")
    return Path(inbox).expanduser().parent / "dashboard" if inbox else None


def find_chrome():
    for candidate in [os.environ.get("CHROME_BIN")] + CHROME_CANDIDATES:
        if not candidate:
            continue
        if Path(candidate).is_file():
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def print_pdf(chrome, html_path, pdf_path):
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
         "--print-to-pdf-no-header", f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()],
        check=True, capture_output=True, timeout=120)
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise RuntimeError("browser exited without writing the PDF")


def publish(today, source=None, dest=None, chrome=None):
    source = Path(source or paths.OUTPUTS_DIR / "dashboard" / "index.html")
    dest = dest or target_dir()
    if dest is None:
        return ["skipped: set SECRET_SAUCE_DASHBOARD_DIR or SECRET_SAUCE_INBOX to publish to Drive"]
    if not source.exists():
        return [f"skipped: {source} not built"]
    (dest / "archive").mkdir(parents=True, exist_ok=True)
    notes = []
    shutil.copyfile(source, dest / "control-room.html")
    notes.append(f"copied {dest / 'control-room.html'}")

    chrome = chrome or find_chrome()
    if not chrome:
        return notes + ["no PDF: Chrome/Chromium not found (set CHROME_BIN)"]
    with tempfile.TemporaryDirectory() as work:  # print outside Drive so no partial file syncs
        tmp = Path(work) / "control-room.pdf"
        try:
            print_pdf(chrome, source, tmp)
        except (subprocess.SubprocessError, OSError, RuntimeError) as exc:
            return notes + [f"no PDF: {exc}"]
        shutil.copyfile(tmp, dest / "archive" / f"control-room-{today.isoformat()}.pdf")
        shutil.copyfile(tmp, dest / "control-room.pdf")  # overwrite in place so the Drive link survives
    pruned = prune_archive(dest / "archive", today)
    return notes + [f"printed {dest / 'control-room.pdf'}"] + ([f"pruned {pruned} old PDF(s)"] if pruned else [])


def prune_archive(archive, today, keep_days=ARCHIVE_DAYS):
    cutoff, removed = today - timedelta(days=keep_days), 0
    for pdf in archive.glob("control-room-*.pdf"):
        try:
            day = date.fromisoformat(pdf.stem.removeprefix("control-room-"))
        except ValueError:
            continue
        if day < cutoff:
            pdf.unlink()
            removed += 1
    return removed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", type=date.fromisoformat,
                        default=datetime.now(ZoneInfo("Asia/Kolkata")).date())
    for line in publish(parser.parse_args().today):
        print(line)
