"""Lightweight phone/email handle normalization (no external deps)."""
from __future__ import annotations

import re

from .config import DEFAULT_REGION_PREFIX

_NON_DIAL = re.compile(r"[^\d+]")


def normalize_handle(raw: str | None) -> str:
    """Canonicalize a handle for matching: E.164-ish numbers, lowercased emails."""
    if not raw:
        return ""
    raw = raw.strip()
    if "@" in raw:
        return raw.lower()
    digits = _NON_DIAL.sub("", raw)
    if digits.startswith("+"):
        return "+" + re.sub(r"\D", "", digits[1:])
    digits = re.sub(r"\D", "", digits)
    if len(digits) == 10:
        return DEFAULT_REGION_PREFIX + digits
    if len(digits) == 11 and digits.startswith(DEFAULT_REGION_PREFIX[1:]):
        return "+" + digits
    return "+" + digits if digits else raw


def last10(handle: str) -> str | None:
    """Last 10 digits of a numeric handle, for fuzzy contact matching."""
    if "@" in handle:
        return None
    digits = re.sub(r"\D", "", handle)
    return digits[-10:] if len(digits) >= 10 else None
