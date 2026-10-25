"""Swiggy/Zomato ads and funnel exports -> the two inputs budget work needs.

Usage: python scripts/parse_ads_exports.py <client> <month YYYY-MM> <out_dir>

Writes:
- <out_dir>/daily.csv: funnel.DAILY_COLUMNS, one row per outlet per platform per day.
- <out_dir>/last_budget.csv: platform, outlet_id, product, amount (from last month's
  budget workbook).

Not implemented yet: written against the first real TBS exports (Swiggy CPC, CBA, funnel
and CPC menu-visits pull; Zomato ads and funnel; last month's budget workbook). Rules:
- Identify outlets by platform ID from clients/<client>/config.yaml; drop excluded IDs.
- Swiggy CPC has no impressions/clicks: put the menu-visits pull in cpc_menu_visits.
- Money via recon_schema.to_decimal. Unknown columns are reported, never guessed.
"""
import sys


def parse(client, month, out_dir):
    raise NotImplementedError(
        f"Export parser awaits {client} exports in inbox/{client}/ (see TODO.md)"
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    parse(*sys.argv[1:])
