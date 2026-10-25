#!/usr/bin/env bash
# Headless 06:00 run: claude -p "/morning", logged to logs/runs/<date>.log.
# Always leaves outputs/brief/<date>.md: on any failure it writes a FAILED brief itself.
# Uses config/headless-settings.json: no prompts, no network tools, no edits outside
# outputs/ and logs/. These rules govern Claude's tools only, not what a script does.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

if [ -f .env ]; then
  set -a; . ./.env; set +a
fi
if [ -f .venv/bin/activate ]; then
  . .venv/bin/activate
fi

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
BRIEF_DIR="${BRIEF_DIR:-$REPO/outputs/brief}"
LOG_DIR="${LOG_DIR:-$REPO/logs/runs}"
TODAY="$(TZ=Asia/Kolkata date +%F)"
LOG="$LOG_DIR/$TODAY.log"
BRIEF="$BRIEF_DIR/$TODAY.md"
mkdir -p "$BRIEF_DIR" "$LOG_DIR"

echo "=== /morning $(TZ=Asia/Kolkata date '+%F %T %Z') ===" >> "$LOG"
"$CLAUDE_BIN" -p "/morning" --permission-mode dontAsk --settings "$REPO/config/headless-settings.json" >> "$LOG" 2>&1
rc=$?

if [ "$rc" -ne 0 ] || [ ! -s "$BRIEF" ]; then
  [ "$rc" -eq 0 ] && rc=1
  {
    echo "# Morning brief $TODAY: FAILED"
    echo
    echo "The 06:00 run did not finish (exit code $rc). Nothing below was reviewed by an agent."
    echo
    echo "Last 30 lines of $LOG:"
    echo
    echo '```'
    tail -n 30 "$LOG"
    echo '```'
  } > "$BRIEF"
fi
exit "$rc"
