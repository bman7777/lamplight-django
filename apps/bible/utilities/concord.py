"""Concordance ID utilities."""

import re

CONCORD_TAG_RE = re.compile(r"<([HGhg]\d+)>")


def normalize_concord_id(concord_id: str) -> str | None:
    """Normalize H1/h1/H734 to the canonical 4-digit form (H0001, H0734).

    Returns None if the input is not a well-formed Strong's ID.
    """
    if not concord_id:
        return None
    prefix, digits = concord_id[:1].upper(), concord_id[1:]
    if prefix not in ("G", "H") or not digits.isdigit():
        return None
    return f"{prefix}{int(digits):04d}"
