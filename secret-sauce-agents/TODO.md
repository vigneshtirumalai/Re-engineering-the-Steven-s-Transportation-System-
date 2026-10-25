# To do

## Data and IDs (Vicky)

- [x] Swiggy 1062415 = Tempt Anna Nagar East
- [ ] Tempt Swiggy IDs: Anna Nagar West, Besant Nagar, Nandanam, Guindy, Alandur, Nungambakkam
- [ ] Tempt Swiggy payout cycle
- [ ] Tempt Swiggy settlement files (outstanding)
- [ ] 2-3 weeks of Tempt Zomato settlement files in Drive `inbox/tempt/zomato/`
- [ ] Hand-built outputs for those weeks in Drive `fixtures/` as `tempt_golden_<period_start>.xlsx`
- [ ] TBS: legal entity, remaining outlets, Swiggy presence for Purasavakkam, Selaiyur, Adyar
- [ ] CK: legal entity, outlets and platform IDs
- [ ] Outlet Registry sheet: set Anna Nagar East swiggy_id to 1062415, delete the unassigned row
- [ ] Do Tempt's accountants want cash keep rate, economic keep rate, or both?

## Setup

- [ ] Connect the Google Sheets connector (claude.ai/customize/connectors), then start a new session
- [ ] Copy the restaurant-consultant and restaurant-second-brain SKILL.md folders into `.claude/skills/`
- [ ] Decide which machine runs the 06:00 job; install Google Drive for desktop and set `.env` there

## Build

- [x] Prompt 0: scaffold
- [ ] Prompt 1: payout recon. Schema, workbook builder, tie-out tests, agents and /recon done; Zomato parser and golden test wait for settlement files
- [ ] Prompt 2: client digest
- [ ] Prompt 3: ad budget and funnel. Rules, funnel + day-of-week scaling, budget draft, agent and /adbudget done; export parser waits for TBS October exports
- [ ] Prompt 4: orchestrator and schedule
