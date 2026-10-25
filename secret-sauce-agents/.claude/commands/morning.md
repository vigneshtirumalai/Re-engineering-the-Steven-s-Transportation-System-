---
description: The 06:00 run - digests, recon on new settlement files, monthly ad budget, prediction scoring, then one brief
---

Run the morning workflow. Follow CLAUDE.md. Continue past any single failure; record
every step's status. Never send anything and never open a browser.

1. Run `.venv/bin/python scripts/morning_plan.py plan`. It returns JSON listing each step,
   whether it runs today and why. Do only what it says; do not decide dates yourself.
2. For each step with `"run": true`, in order:
   - `digest`: run `/digest all --headless`.
   - `recon`: for the listed client, platform and files, determine each file's settlement
     period_start and run `/recon <client> <period_start>`. When a recon finishes (pass or
     fail, but not a crash), run `.venv/bin/python scripts/morning_plan.py mark-done
     <client> <platform> <files...>` so the files are not reprocessed.
   - `adbudget`: run `/adbudget <client> <budget_month>`.
   - `score_predictions`: run `.venv/bin/python scripts/score_predictions.py`.
   If a step fails, note the error in one line and move on.
3. Write `outputs/brief/<today>.md` (today in Asia/Kolkata), in this order:
   1. **Status**: one line per step from the plan: OK, SKIPPED (with the plan's reason)
      or FAILED (with the error).
   2. **Decide today**: at most 5 bullets, the things that need Vicky's judgment.
   3. **WhatsApp drafts ready to send**: each draft's path and text, plus any
      verify-before-sending items.
   4. **Recon checker results**: client, week, PASS/FAIL and the first issue if FAIL.
   5. **Predictions scored**: the scorer's output line.
   6. **Missing or failed**: every MISSING.md item and the plan's `missing` lists, with
      the exact file needed and where it goes.
   Numbers in the brief are quoted from outputs, never computed by you.
4. Run `.venv/bin/python scripts/build_dashboard.py` to refresh `outputs/dashboard/index.html`.
