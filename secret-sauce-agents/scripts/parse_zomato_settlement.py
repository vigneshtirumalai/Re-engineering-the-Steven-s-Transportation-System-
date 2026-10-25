"""Zomato weekly settlement annexure -> tidy recon rows (see recon_schema.TIDY_COLUMNS).

Usage: python scripts/parse_zomato_settlement.py <client> <period_start> <tidy.csv>

Not implemented yet: the line-to-field mapping is written against real annexures, which
have not arrived. Rules for the implementation:
- Identify outlets by Zomato Res ID from clients/<client>/config.yaml, never by name.
- Parse amounts with recon_schema.to_decimal; store deductions as positive numbers.
- Any line that does not map to a schema field is emitted with field=UNMAPPED and its
  raw_label, never dropped and never forced into a field.
"""
import sys

PLATFORM = "zomato"


def parse(client, period_start):
    raise NotImplementedError(
        "Zomato parser awaits settlement files in inbox/<client>/zomato/ (see TODO.md)"
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    parse(sys.argv[1], sys.argv[2])
