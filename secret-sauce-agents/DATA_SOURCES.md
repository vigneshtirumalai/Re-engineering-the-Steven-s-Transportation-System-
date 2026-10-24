# Data sources

Raw files and human-maintained tables live in Google Drive, in the private folder
**Secret Sauce Agents** (folder ID `1-Cugslu2x4i2QenDMNH6nUlb02YOV0GB`).

| What | Where in Drive | Format | Used by |
| --- | --- | --- | --- |
| Settlement annexures, MTD funnel, CPC/CBA, ads exports | `inbox/<client>/<platform>/` | Original .xlsx/.csv, never converted to Sheets | Parsers via `scripts/paths.py` |
| Hand-built golden recon outputs | `fixtures/` (name `tempt_golden_<period_start>.xlsx`) | Original .xlsx | `tests/test_recon.py` |
| Outlet Registry | Google Sheet in the root folder | Sheet | Source for `clients/<client>/config.yaml` |
| Predictions Log, Review Log | Google Sheets in the root folder | Sheet | Mirror of `logs/*.csv` |

## Rules

- Upload exports exactly as downloaded from Swiggy/Zomato. Do not open-and-save them in
  Sheets: conversion can change IDs, dates and paise, and breaks the source_file/source_row trail.
- The Outlet Registry is where IDs get filled in. `clients/<client>/config.yaml` is what
  scripts read; after editing the registry, ask Claude to sync it into the configs (a
  session with the Google Drive connector can read the sheet).
- `logs/*.csv` in the repo stay the system of record for the workflows; the Sheets are the
  view you review on Sunday. Syncing them is a later step (Prompt 4).

## Running locally

Install Google Drive for desktop, sync **Secret Sauce Agents**, copy `.env.example` to
`.env` and set `SECRET_SAUCE_INBOX` and `SECRET_SAUCE_FIXTURES` to the synced paths.
