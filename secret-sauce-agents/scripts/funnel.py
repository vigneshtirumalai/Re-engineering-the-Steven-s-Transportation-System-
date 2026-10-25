"""Daily funnel rows -> one row per outlet per platform for a month, MTD and scaled.

Usage: python scripts/funnel.py <daily.csv> <month YYYY-MM> <funnel.csv> [<previous_funnel.csv>]

Input columns (DAILY_COLUMNS) come from the export parsers; one row per outlet per day.
Additive metrics are scaled from the MTD cut-off to the full month by day-of-week
weighting. Money is Decimal throughout.
"""
import calendar
import csv
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recon_schema import to_decimal  # noqa: E402

DAILY_COLUMNS = [
    "client", "platform", "outlet_id", "outlet_name", "date", "impressions",
    "menu_visits", "cart", "orders", "gmv", "cpc_spend", "cba_spend",
    "cpc_attributed_gmv", "cba_attributed_gmv", "cpc_menu_visits",
]
ADDITIVE = DAILY_COLUMNS[5:]
MOM_METRICS = ["orders", "gmv", "ad_spend", "menu_conv", "cart_conv", "order_conv", "roas"]


def _ratio(num, den):
    return num / den if den else None


def scale_to_month(daily, month):
    """daily: {date: Decimal}. Returns (projected full-month total, factor vs MTD sum)."""
    year, mon = (int(x) for x in month.split("-"))
    days_in_month = calendar.monthrange(year, mon)[1]
    weekday_counts = defaultdict(int)
    for d in range(1, days_in_month + 1):
        weekday_counts[date(year, mon, d).weekday()] += 1

    mtd = sum(daily.values(), Decimal("0"))
    if not daily:
        return Decimal("0"), None
    by_weekday = defaultdict(list)
    for d, v in daily.items():
        by_weekday[d.weekday()].append(v)
    overall_avg = mtd / len(daily)
    projected = Decimal("0")
    for weekday, count in weekday_counts.items():
        values = by_weekday.get(weekday)
        avg = sum(values, Decimal("0")) / len(values) if values else overall_avg
        projected += avg * count
    return projected, _ratio(projected, mtd)


def read_daily(path, month):
    with open(path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["date"].startswith(month)]
    for r in rows:
        r["date"] = date.fromisoformat(r["date"])
        for col in ADDITIVE:
            r[col] = to_decimal(r.get(col, ""))
    return rows


def summarise(rows, month, lookback_days=14):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["platform"], r["outlet_id"])].append(r)

    out = []
    for (platform, outlet_id), items in sorted(groups.items()):
        cutoff = max(r["date"] for r in items)
        rec = {
            "client": items[0]["client"], "platform": platform, "outlet_id": outlet_id,
            "outlet_name": items[0]["outlet_name"], "month": month,
            "mtd_cutoff": cutoff.isoformat(), "mtd_days": len({r["date"] for r in items}),
        }
        for col in ADDITIVE:
            daily = defaultdict(Decimal)
            for r in items:
                daily[r["date"]] += r[col]
            rec[f"mtd_{col}"] = sum(daily.values(), Decimal("0"))
            rec[f"scaled_{col}"], factor = scale_to_month(daily, month)
            if col == "gmv":
                rec["gmv_scaling_factor"] = factor

        since = cutoff - timedelta(days=lookback_days - 1)
        recent = [r for r in items if r["date"] >= since]
        recent_days = len({r["date"] for r in recent})
        rec["orders_per_day_recent"] = _ratio(sum((r["orders"] for r in recent), Decimal("0")), recent_days)

        s = {col: rec[f"scaled_{col}"] for col in ADDITIVE}
        rec["menu_conv"] = _ratio(s["menu_visits"], s["impressions"])
        rec["cart_conv"] = _ratio(s["cart"], s["menu_visits"])
        rec["order_conv"] = _ratio(s["orders"], s["cart"])
        rec["orders"] = s["orders"]
        rec["gmv"] = s["gmv"]
        rec["ad_spend"] = s["cpc_spend"] + s["cba_spend"]
        rec["cpc_roas"] = _ratio(s["cpc_attributed_gmv"], s["cpc_spend"])
        rec["cba_roas"] = _ratio(s["cba_attributed_gmv"], s["cba_spend"])
        rec["roas"] = _ratio(s["cpc_attributed_gmv"] + s["cba_attributed_gmv"], rec["ad_spend"])
        rec["ad_pct_gmv"] = _ratio(rec["ad_spend"], s["gmv"])
        # Swiggy CPC has no clicks; menu visits from the CPC pull stand in for them.
        rec["cpc_clicks_proxy"] = s["cpc_menu_visits"] if platform == "swiggy" else None
        out.append(rec)
    return out


def add_mom(current, previous):
    prev = {(p["platform"], p["outlet_id"]): p for p in previous}
    for rec in current:
        p = prev.get((rec["platform"], rec["outlet_id"]))
        for m in MOM_METRICS:
            old = to_decimal(p[m]) if p and p.get(m) not in (None, "", "None") else None
            rec[f"{m}_mom"] = _ratio(rec[m] - old, old) if old and rec[m] is not None else None
    return current


def write_csv(records, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    records = summarise(read_daily(sys.argv[1], sys.argv[2]), sys.argv[2])
    if len(sys.argv) == 5:
        with open(sys.argv[4], newline="") as f:
            records = add_mom(records, list(csv.DictReader(f)))
    write_csv(records, sys.argv[3])
    print(sys.argv[3])
