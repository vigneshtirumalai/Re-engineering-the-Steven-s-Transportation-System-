---
description: Draft next month's ad budget and memo for a client
argument-hint: <client> <budget_month YYYY-MM>
---

Run the `ad-budget` subagent for client `$1`, budgeting month `$2`.

When it finishes, show me `outputs/$1/$2/memo.md`, the differences from carry-forward, the
path to `budget_draft.xlsx`, and any `MISSING.md`.
