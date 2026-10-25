"""Fixed recon schema shared by the settlement parsers and the workbook builder.

Every parser emits tidy rows (TIDY_COLUMNS), one per settlement line, with `field` set to
one of the keys below or to UNMAPPED. Amounts are Decimal rupees. Deductions are stored
as positive numbers and subtracted, whatever sign the platform file uses.
"""
import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation

TIDY_COLUMNS = [
    "client", "platform", "outlet_id", "outlet_name", "period_start", "period_end",
    "payout_date", "field", "amount", "raw_label", "source_file", "source_row",
]

REVENUE = {
    "gross_taxable_sales": "Gross Taxable Sales",
    "gst_9_5_collected": "GST u/s 9(5)",
}
DEDUCTIONS = {
    "commission": "Commission",
    "gst_on_commission": "GST on Commission",
    "ads_discount": "Ads/Discount",
    "delivery_packaging": "Delivery/Packaging",
    "other_recoveries": "Other Recoveries",
    "tds_194o": "TDS 194O",
    "tcs": "TCS",
    "gst_9_5_remitted": "GST 9(5)",
}
CREDIT = {"net_settlement": "Net Settlement"}
BRIDGE = {
    "prior_period_adjustments": "Prior-period Adjustments",
    "carried_forward_recoveries": "Carried-forward Recoveries",
    "payout_amount": "Payout Amount",
}
UNMAPPED = "UNMAPPED"

PARSED_FIELDS = {**REVENUE, **DEDUCTIONS, **CREDIT, **BRIDGE}
TOLERANCE = Decimal("1")


def to_decimal(value):
    """Parse a money cell as Decimal; blanks are zero. Never goes through float."""
    text = str(value).strip().replace(",", "").replace("₹", "")
    if text in ("", "-", "None", "nan"):
        return Decimal("0")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"not a money value: {value!r}") from exc


def read_tidy(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["amount"] = to_decimal(row["amount"])
    return rows


def write_tidy(rows, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TIDY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "amount": str(row["amount"])})


def outlet_totals(rows):
    """Sum mapped fields per (platform, outlet_id) and add computed totals and keep rates."""
    sums = defaultdict(lambda: defaultdict(Decimal))
    names = {}
    for row in rows:
        if row["field"] == UNMAPPED:
            continue
        if row["field"] not in PARSED_FIELDS:
            raise ValueError(f"unknown field {row['field']!r} in {row['source_file']}")
        key = (row["platform"], row["outlet_id"])
        sums[key][row["field"]] += row["amount"]
        names[key] = row["outlet_name"]

    totals = {}
    for key, fields in sums.items():
        t = {f: fields[f] for f in PARSED_FIELDS}
        t["total_gross"] = sum((t[f] for f in REVENUE), Decimal("0"))
        t["total_deductions"] = sum((t[f] for f in DEDUCTIONS), Decimal("0"))
        t["computed_net"] = t["total_gross"] - t["total_deductions"]
        gts = t["gross_taxable_sales"]
        t["cash_keep_rate"] = t["net_settlement"] / gts if gts else None
        t["economic_keep_rate"] = (
            (t["net_settlement"] + t["tds_194o"] + t["tcs"]) / gts if gts else None
        )
        t["outlet_name"] = names[key]
        totals[key] = t
    return totals


def tie_out_breaks(rows):
    """Outlets where stated Net Settlement differs from Total Gross - Total Deductions by > Rs 1."""
    return {
        key: t["net_settlement"] - t["computed_net"]
        for key, t in outlet_totals(rows).items()
        if abs(t["net_settlement"] - t["computed_net"]) > TOLERANCE
    }


def payout_breaks(rows):
    """Per platform: Net + adjustments + carried-forward vs stated Payout Amount, > Rs 1."""
    by_platform = defaultdict(lambda: defaultdict(Decimal))
    for (platform, _), t in outlet_totals(rows).items():
        for f in ("net_settlement", *BRIDGE):
            by_platform[platform][f] += t[f]
    breaks = {}
    for platform, t in by_platform.items():
        bridged = t["net_settlement"] + t["prior_period_adjustments"] + t["carried_forward_recoveries"]
        if abs(bridged - t["payout_amount"]) > TOLERANCE:
            breaks[platform] = t["payout_amount"] - bridged
    return breaks
