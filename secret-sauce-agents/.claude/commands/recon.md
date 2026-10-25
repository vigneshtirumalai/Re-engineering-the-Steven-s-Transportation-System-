---
description: Build, check and summarise the weekly payout reconciliation for a client
argument-hint: <client> <period_start YYYY-MM-DD>
---

Run the `payout-recon` subagent for client `$1` and settlement week starting `$2`.

When it finishes, show me `outputs/$1/$2/summary.md`, `outputs/$1/$2/checker.md`, the
pytest result, and any `MISSING.md`.
