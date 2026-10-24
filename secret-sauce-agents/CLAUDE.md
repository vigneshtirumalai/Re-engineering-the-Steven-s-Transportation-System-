# Secret Sauce & Co. agents

Claude Code subagents and slash commands that automate recurring analytics work for
Secret Sauce & Co.'s Chennai restaurant clients on Swiggy and Zomato.

Clients: `tempt` (TEMPT FOODS LLP), `tbs` (The Brownie Studio), `ck` (Chorum Kootanum).
Each has `clients/<client>/config.yaml` with outlets and platform IDs.

## Layout

- `inbox/<client>/<platform>/`: raw exports I drop in (settlement annexures, MTD funnel, ads). Gitignored.
- `outputs/<client>/<period>/`: workbooks, summaries, drafts. Gitignored.
- `scripts/`: deterministic Python (pandas, openpyxl). Tests in `tests/` (pytest).
- `tests/fixtures/`: hand-built golden outputs. Gitignored (real client data).
- `logs/predictions.csv`, `logs/review_log.csv`: prediction and review tracking.
- `.claude/agents/`, `.claude/commands/`, `.claude/skills/`: subagents, slash commands, skills.

Run Python through the venv: `.venv/bin/python`, `.venv/bin/pytest`.

## Rules

1. Numbers come from scripts in `scripts/`, never from you adding up values in your head. If a number is not produced by a script, do not state it.
2. Money is parsed as `Decimal` (or integer paise), never float. Round only for display.
3. Every parser has a pytest that checks totals tie out (net settlement = total gross minus total deductions, to within Rs 1 per cell).
4. Never edit tests, tolerances or files in `tests/fixtures/` to make a test pass. If a test fails, show me the failing cells and your hypothesis and stop.
5. Outlets are identified by platform ID, never by display name (Zomato labels every Tempt outlet "Tempt.").
6. Definitions:
   - Cash keep rate = Net Settlement / Gross Taxable Sales.
   - Economic keep rate = (Net Settlement + TDS 194O + TCS) / Gross Taxable Sales, because TDS and TCS are claimable tax credits.
   - GST u/s 9(5) is a pass-through and never counts as revenue in a ratio.
   - Report both keep rates.
7. Use the restaurant-consultant skill for method (unit economics spine: GMV, commission, discounts, ad spend, net payout, keep rate) and the restaurant-second-brain skill for diagnosis and how I reason.
8. Never send anything to a client. Agents write drafts to `outputs/`; I send.
9. Every diagnosis that predicts a metric movement appends a row to `logs/predictions.csv` with `baseline_value`, `direction`, `magnitude`, `horizon_days` and a `hit_rule` a script can check later (e.g. `orders_7d_avg >= baseline * 1.10`). No hit_rule, no prediction.
10. If a required input is missing, write a short `MISSING.md` in the output folder listing exactly which file is needed and where to put it, and stop that workflow.
