"""Log a 9:00 review: python scripts/log_review.py <workflow> <client> <edits_numbers 0-3> <edits_text 0-3> <minutes> [notes] [--output PATH]

Edit scale: 0 sent as is, 1 a word or one number fixed, 2 a line rewritten or a call
changed, 3 redone or not sent.
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

REVIEW_LOG = paths.LOGS_DIR / "review_log.csv"
WORKFLOWS = {"recon", "digest", "adbudget", "morning"}


def edit_score(value):
    n = int(value)
    if not 0 <= n <= 3:
        raise argparse.ArgumentTypeError("edits must be 0-3")
    return n


def main(argv=None, log=REVIEW_LOG):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", choices=sorted(WORKFLOWS))
    parser.add_argument("client")
    parser.add_argument("edits_numbers", type=edit_score)
    parser.add_argument("edits_text", type=edit_score)
    parser.add_argument("minutes", type=int)
    parser.add_argument("notes", nargs="?", default="")
    parser.add_argument("--output", default="", help="path of the output you reviewed")
    args = parser.parse_args(argv)
    row = [datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat(), args.workflow,
           args.client, args.output, args.edits_numbers, args.edits_text, args.minutes, args.notes]
    with open(log, "a", newline="") as f:
        csv.writer(f, lineterminator="\n").writerow(row)
    return row


if __name__ == "__main__":
    print(main())
