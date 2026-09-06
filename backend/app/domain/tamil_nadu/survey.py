"""Tamil Nadu Survey and Subdivision Intelligence.

Normalizes revenue and town survey identifiers and compares parcel sub-divisions.
Differentiates identical parcels, parent parcels, and distinct sub-divisions.
"""
from enum import Enum
import re
from typing import Optional, Tuple


class SurveyComparisonGrade(str, Enum):
    MATCH = "MATCH"
    PARENT_PARCEL = "PARENT_PARCEL"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


def normalize_survey_identifier(raw: Optional[str]) -> Optional[str]:
    """Normalize raw Tamil Nadu survey string into standard canonical format.

    Examples:
    'S.No. 124/3A' -> '124/3A'
    'S.F.No. 124/3A' -> '124/3A'
    'R.S.No. 124/3A' -> '124/3A'
    'T.S.No. 124/3A' -> '124/3A'
    'Survey No: 124/3A' -> '124/3A'
    'Survey Number 124/3A' -> '124/3A'
    'S.No 124 / 3 A' -> '124/3A'
    """
    if not raw or not raw.strip():
        return None

    cleaned = raw.strip()

    # Strip prefixes (case-insensitive)
    cleaned = re.sub(
        r"^(s\.?\s*f?\.?\s*no\.?|r\.?\s*s\.?\s*no\.?|t\.?\s*s\.?\s*no\.?|survey\s*(no\.?|number)?)\s*[:\-]?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Normalize slashes and hyphens
    cleaned = re.sub(r"\s*/\s*", "/", cleaned)
    cleaned = re.sub(r"\s*-\s*", "-", cleaned)

    # Collapse space between number and subdivision letters (e.g. '3 A' -> '3A')
    cleaned = re.sub(r"(\d+)\s+([A-Za-z])", r"\1\2", cleaned)
    cleaned = re.sub(r"([A-Za-z])\s+(\d+)", r"\1\2", cleaned)

    # Remove any lingering spaces
    cleaned = re.sub(r"\s+", "", cleaned)

    return cleaned.upper() if cleaned else None


def compare_survey_parcels(
    s1: Optional[str], s2: Optional[str]
) -> Tuple[SurveyComparisonGrade, str]:
    """Compare two survey identifiers with Tamil Nadu sub-division sensitivity.

    Returns (grade, explanation) where grade is SurveyComparisonGrade.
    """
    n1 = normalize_survey_identifier(s1)
    n2 = normalize_survey_identifier(s2)

    if not n1 or not n2:
        return SurveyComparisonGrade.UNKNOWN, "Survey number not provided in one or both records."

    if n1 == n2:
        return SurveyComparisonGrade.MATCH, f"Survey number '{n1}' matches exactly."

    parts1 = n1.split("/")
    parts2 = n2.split("/")

    base1, sub1 = parts1[0], "/".join(parts1[1:]) if len(parts1) > 1 else ""
    base2, sub2 = parts2[0], "/".join(parts2[1:]) if len(parts2) > 1 else ""

    if base1 == base2:
        if not sub1 or not sub2:
            return (
                SurveyComparisonGrade.PARENT_PARCEL,
                f"Parent parcel relationship identified ({n1} vs {n2}). Requires chain verification for sub-division.",
            )

        # Prefix/refinement check: e.g. 124/3 vs 124/3A, or 124/3A vs 124/3A1
        if sub1.startswith(sub2) or sub2.startswith(sub1):
            return (
                SurveyComparisonGrade.PARENT_PARCEL,
                f"Parent parcel or parent-to-subdivision refinement identified ({n1} vs {n2}). Requires chain verification.",
            )

        # Distinct sub-divisions: e.g. 124/3A vs 124/3B
        return (
            SurveyComparisonGrade.MISMATCH,
            f"Survey subdivision mismatch: '{n1}' vs '{n2}'. Different sub-divisions designate distinct parcels in Tamil Nadu.",
        )

    return (
        SurveyComparisonGrade.MISMATCH,
        f"Base survey number mismatch: '{n1}' vs '{n2}'.",
    )
