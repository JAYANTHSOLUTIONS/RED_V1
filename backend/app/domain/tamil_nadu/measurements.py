"""Tamil Nadu land measurement conversion and comparison intelligence.

Provides deterministic Decimal conversions between standard Tamil Nadu property units:
- Square Feet (sq.ft)
- Square Metres (sq.m)
- Cents (1 cent = 435.6 sq.ft)
- Grounds (1 ground = 2,400.0 sq.ft)
- Acres (1 acre = 100 cents = 43,560.0 sq.ft)
- Hectares (1 hectare = 2.47105 acres = 107,639.1 sq.ft)

Strictly returns UNKNOWN_UNIT on uninterpretable units without guessing.
"""
from decimal import Decimal
from typing import Optional, Tuple

SQFT_PER_CENT = Decimal("435.6")
SQFT_PER_GROUND = Decimal("2400.0")
SQFT_PER_ACRE = Decimal("43560.0")
SQFT_PER_HECTARE = Decimal("107639.1")
SQFT_PER_SQM = Decimal("10.7639")


def convert_to_sqft(extent: Decimal, unit_str: Optional[str]) -> Tuple[Optional[Decimal], str]:
    """Convert extent to square feet using exact Tamil Nadu conversion factors.

    Returns (sqft_decimal, canonical_unit). If unrecognized, returns (None, 'UNKNOWN_UNIT').
    """
    if not unit_str or not unit_str.strip():
        return None, "UNKNOWN_UNIT"

    u = unit_str.strip().lower()
    ext = Decimal(str(extent))

    if ext <= Decimal("0.0"):
        return None, "INVALID_EXTENT"

    if u in ("sq.ft", "sqft", "square feet", "square foot", "sq ft"):
        return ext, "sq.ft"

    if u in ("cent", "cents"):
        return ext * SQFT_PER_CENT, "cent"

    if u in ("ground", "grounds"):
        return ext * SQFT_PER_GROUND, "ground"

    if u in ("acre", "acres"):
        return ext * SQFT_PER_ACRE, "acre"

    if u in ("hectare", "hectares", "ha"):
        return ext * SQFT_PER_HECTARE, "hectare"

    if u in ("sq.m", "sqm", "square metres", "square meters", "sq m"):
        return ext * SQFT_PER_SQM, "sq.m"

    return None, "UNKNOWN_UNIT"


def compare_property_extents(
    extent1: Optional[Decimal],
    unit1: Optional[str],
    extent2: Optional[Decimal],
    unit2: Optional[str],
) -> Tuple[str, Decimal, str]:
    """Compare two land extents with Decimal precision.

    Returns:
    - result: 'MATCH', 'REVIEW', 'SIGNIFICANT_MISMATCH', 'UNKNOWN'
    - discrepancy_pct: Decimal percentage difference
    - explanation: Human-readable narrative
    """
    if extent1 is None or extent2 is None:
        return "UNKNOWN", Decimal("0.0"), "Extent value missing in one or both records."

    sqft1, u1 = convert_to_sqft(extent1, unit1)
    sqft2, u2 = convert_to_sqft(extent2, unit2)

    if u1 == "UNKNOWN_UNIT" or u2 == "UNKNOWN_UNIT":
        return "UNKNOWN", Decimal("0.0"), f"Uninterpretable measurement unit encountered ('{unit1}' or '{unit2}')."

    if sqft1 is None or sqft2 is None:
        return "UNKNOWN", Decimal("0.0"), "Invalid non-positive extent value encountered."

    max_sqft = max(sqft1, sqft2)
    diff_sqft = abs(sqft1 - sqft2)
    pct_diff = (diff_sqft / max_sqft) * Decimal("100.0")

    if pct_diff <= Decimal("2.0"):
        return (
            "MATCH",
            pct_diff,
            f"Extent matches within legal survey tolerance ({sqft1:.1f} sq.ft vs {sqft2:.1f} sq.ft, diff: {pct_diff:.2f}%).",
        )
    if pct_diff <= Decimal("10.0"):
        return (
            "REVIEW",
            pct_diff,
            f"Minor extent discrepancy of {pct_diff:.2f}% ({sqft1:.1f} sq.ft vs {sqft2:.1f} sq.ft). Requires boundary reconciliation.",
        )
    return (
        "SIGNIFICANT_MISMATCH",
        pct_diff,
        f"Significant extent discrepancy of {pct_diff:.2f}% ({sqft1:.1f} sq.ft vs {sqft2:.1f} sq.ft) exceeds acceptable survey tolerance.",
    )
