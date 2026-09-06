"""Database sequence definitions and reference formatting.

Provides database-backed, concurrency-safe public reference generation
conforming to the Master Specification (e.g. `PR-2026-000123`).
"""
from datetime import datetime, timezone
from sqlalchemy import Sequence

property_ref_seq = Sequence("property_ref_seq", start=1, increment=1)


def format_property_reference(seq_val: int, year: int | None = None) -> str:
    """Format a sequence number into the public reference ID.

    Example: 123 -> 'PR-2026-000123'
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    return f"PR-{year}-{seq_val:06d}"
