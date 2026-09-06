"""Owner and Pattadar naming intelligence for Tamil Nadu real estate.

Handles Tamil Nadu naming conventions:
- Initials formatting (R. Kumar, R Kumar, R.Kumar, Kumar R, R KUMAR)
- Distinct initial conflict detection (R. Kumar != S. Kumar)
- Native Tamil script preservation and exact Unicode normalization (e.g. 'ராமசாமி')
"""
import unicodedata
from typing import List, Optional, Tuple


def is_tamil_unicode(text: Optional[str]) -> bool:
    """Return True if the text contains characters within the Unicode Tamil block (U+0B80 - U+0BFF)."""
    if not text:
        return False
    return any(0x0B80 <= ord(c) <= 0x0BFF for c in text)


def normalize_name_tokens(raw: Optional[str]) -> List[str]:
    """Tokenize and normalize name strings, preserving Tamil Unicode characters."""
    if not raw or not raw.strip():
        return []

    # NFC Unicode normalization preserves composite Tamil glyphs
    normalized = unicodedata.normalize("NFC", raw.strip())
    # Replace period and commas with spaces
    cleaned = normalized.replace(".", " ").replace(",", " ").replace("-", " ")
    # Lowercase Latin characters without altering non-Latin scripts
    cleaned = cleaned.lower()
    tokens = [t.strip() for t in cleaned.split() if t.strip()]
    return tokens


def compare_tamil_nadu_names(name1: Optional[str], name2: Optional[str]) -> Tuple[str, str]:
    """Compare two owner/pattadar names with Tamil Nadu initial and script awareness.

    Returns (result, explanation) where result is:
    - 'MATCH': Identical tokens, initials order variants, or exact Unicode matches
    - 'POSSIBLE_MATCH': Name expansion (e.g. 'Rajesh Kumar' vs 'R Kumar')
    - 'MISMATCH': Distinct initials (e.g. 'R. Kumar' vs 'S. Kumar') or different names
    - 'UNKNOWN': Missing name data
    """
    if not name1 or not name2 or not name1.strip() or not name2.strip():
        return "UNKNOWN", "Owner name missing in one or both records."

    # Direct raw Unicode match (covers native Tamil script: e.g. 'ராமசாமி' == 'ராமசாமி')
    if unicodedata.normalize("NFC", name1.strip()) == unicodedata.normalize("NFC", name2.strip()):
        return "MATCH", f"Owner names match exactly ('{name1}')."

    tokens1 = normalize_name_tokens(name1)
    tokens2 = normalize_name_tokens(name2)

    if not tokens1 or not tokens2:
        return "UNKNOWN", "Name normalization yielded no valid tokens."

    # Exact token match
    if tokens1 == tokens2:
        return "MATCH", f"Owner name matches ('{name1}')."

    # Set equivalence (handles 'Kumar R' vs 'R Kumar')
    set1, set2 = set(tokens1), set(tokens2)
    if set1 == set2:
        return "MATCH", f"Owner name matches with differing token order ('{name1}' vs '{name2}')."

    # Initial conflict analysis
    single_chars1 = {t for t in tokens1 if len(t) == 1}
    single_chars2 = {t for t in tokens2 if len(t) == 1}
    non_single1 = {t for t in tokens1 if len(t) > 1}
    non_single2 = {t for t in tokens2 if len(t) > 1}

    # If base name matches but single initials conflict -> MISMATCH
    if non_single1 and non_single1 == non_single2:
        if single_chars1 and single_chars2 and single_chars1 != single_chars2:
            return (
                "MISMATCH",
                f"Conflicting initial detected in owner name ('{name1}' vs '{name2}'). Distinct initials designate different individuals.",
            )
        return (
            "POSSIBLE_MATCH",
            f"Owner name matches without initial confirmation ('{name1}' vs '{name2}'). Requires documentary verification.",
        )

    # Initial expansion check (e.g. 'Rajesh Kumar' vs 'R Kumar')
    if len(tokens1) == len(tokens2):
        matches = 0
        possible_expansions = 0
        for t1, t2 in zip(tokens1, tokens2):
            if t1 == t2:
                matches += 1
            elif (len(t1) == 1 and t2.startswith(t1)) or (len(t2) == 1 and t1.startswith(t2)):
                possible_expansions += 1
        if matches + possible_expansions == len(tokens1):
            return (
                "POSSIBLE_MATCH",
                f"Possible name expansion detected ('{name1}' vs '{name2}'). Requires legal counsel verification.",
            )

    return "MISMATCH", f"Owner name mismatch ('{name1}' vs '{name2}')."
