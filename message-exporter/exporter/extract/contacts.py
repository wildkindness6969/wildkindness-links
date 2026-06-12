"""Resolve phone numbers / emails to names via AddressBook.sqlitedb.

Everything here is best-effort: if the address book is missing or its
schema is unexpected, we return an empty map and the export falls back
to formatted numbers.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from ..phonenumbers_util import last10, normalize_handle


def load_contact_names(addressbook_db: Path | None) -> dict[str, str]:
    """Return {normalized handle: display name}, plus last-10-digit aliases."""
    if not addressbook_db or not Path(addressbook_db).exists():
        return {}
    try:
        conn = sqlite3.connect(f"file:{addressbook_db}?mode=ro", uri=True)
    except sqlite3.Error:
        return {}
    try:
        return _load(conn)
    except sqlite3.Error:
        return {}
    finally:
        conn.close()


def _load(conn: sqlite3.Connection) -> dict[str, str]:
    names: dict[str, str] = {}
    rows = conn.execute(
        """SELECT p.ROWID, p.First, p.Last, p.Organization, mv.value
           FROM ABPerson p
           JOIN ABMultiValue mv ON mv.record_id = p.ROWID
           WHERE mv.value IS NOT NULL"""
    )
    for rowid, first, last, org, value in rows:
        display = " ".join(part for part in (first, last) if part).strip() or (org or "").strip()
        if not display:
            continue
        handle = normalize_handle(str(value))
        if not handle:
            continue
        names.setdefault(handle, display)
        alias = last10(handle)
        if alias:
            names.setdefault(alias, display)
    return names


def lookup_name(names: dict[str, str], handle: str) -> str | None:
    """Find a contact name for a normalized handle, with last-10-digit fallback."""
    if handle in names:
        return names[handle]
    alias = last10(handle)
    if alias and alias in names:
        return names[alias]
    return None
