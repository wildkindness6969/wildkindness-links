"""Resolve files inside an unencrypted iTunes/Finder backup via Manifest.db."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def resolve_file(backup_dir: Path, domain: str, relative_path: str) -> Path | None:
    """Map (domain, relativePath) to the hashed file on disk, or None."""
    manifest_db = backup_dir / "Manifest.db"
    if not manifest_db.exists():
        return None
    conn = sqlite3.connect(f"file:{manifest_db}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT fileID FROM Files WHERE domain = ? AND relativePath = ?",
            (domain, relative_path),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    file_id = row[0]
    nested = backup_dir / file_id[:2] / file_id   # iOS 10+ layout
    if nested.exists():
        return nested
    flat = backup_dir / file_id                   # pre-iOS 10 layout
    if flat.exists():
        return flat
    return None
