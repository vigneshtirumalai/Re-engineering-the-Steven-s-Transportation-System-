"""Where workflows read raw data from.

Raw exports live in the Google Drive folder "Secret Sauce Agents/inbox". On the machine
that runs the workflows, Google Drive for desktop syncs that folder locally; point
SECRET_SAUCE_INBOX at the synced path (see .env.example). Without it, the repo's own
inbox/ is used, which is what tests and cloud sessions rely on.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _dir_from_env(var, default):
    value = os.environ.get(var)
    return Path(value).expanduser() if value else default


INBOX_DIR = _dir_from_env("SECRET_SAUCE_INBOX", REPO_ROOT / "inbox")
FIXTURES_DIR = _dir_from_env("SECRET_SAUCE_FIXTURES", REPO_ROOT / "tests" / "fixtures")
OUTPUTS_DIR = REPO_ROOT / "outputs"
LOGS_DIR = REPO_ROOT / "logs"
CLIENTS_DIR = REPO_ROOT / "clients"


def inbox(client, platform):
    return INBOX_DIR / client / platform
