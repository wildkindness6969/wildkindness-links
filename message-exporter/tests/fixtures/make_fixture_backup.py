"""Wrap the fixture sms.db (and a small AddressBook) into a fake,
unencrypted Finder-style backup directory with a real Manifest.db."""
from __future__ import annotations

import hashlib
import plistlib
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import make_fixture_smsdb

DOMAIN = "HomeDomain"
SMS_PATH = "Library/SMS/sms.db"
AB_PATH = "Library/AddressBook/AddressBook.sqlitedb"


def build_addressbook(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE ABPerson (
            ROWID INTEGER PRIMARY KEY, First TEXT, Last TEXT, Organization TEXT
        );
        CREATE TABLE ABMultiValue (
            UID INTEGER PRIMARY KEY, record_id INTEGER, property INTEGER,
            identifier INTEGER, label INTEGER, value TEXT
        );
    """)
    c.executemany("INSERT INTO ABPerson (ROWID, First, Last, Organization) VALUES (?,?,?,?)", [
        (1, "Alice", "Client", None),
        (2, "Bob", "Vendor", None),
        (3, None, None, "Carol Cakes LLC"),
    ])
    c.executemany(
        "INSERT INTO ABMultiValue (record_id, property, value) VALUES (?,?,?)", [
            (1, 3, "+1 (925) 555-1234"),
            (2, 3, "415-555-9876"),
            (3, 4, "Carol@Example.com"),
        ])
    conn.commit()
    conn.close()
    return path


def file_id(domain: str, relative_path: str) -> str:
    return hashlib.sha1(f"{domain}-{relative_path}".encode()).hexdigest()


def build(backup_dir: Path) -> Path:
    backup_dir = Path(backup_dir)
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True)

    work = backup_dir.parent / "_payload"
    sms_db = make_fixture_smsdb.build(work / "sms.db")
    ab_db = build_addressbook(work / "AddressBook.sqlitedb")

    manifest = sqlite3.connect(backup_dir / "Manifest.db")
    manifest.execute("""CREATE TABLE Files (
        fileID TEXT PRIMARY KEY, domain TEXT, relativePath TEXT,
        flags INTEGER, file BLOB)""")
    for src, rel in ((sms_db, SMS_PATH), (ab_db, AB_PATH)):
        fid = file_id(DOMAIN, rel)
        dest = backup_dir / fid[:2] / fid
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(src, dest)
        manifest.execute("INSERT INTO Files VALUES (?,?,?,?,?)",
                         (fid, DOMAIN, rel, 1, None))
    manifest.commit()
    manifest.close()

    (backup_dir / "Info.plist").write_bytes(plistlib.dumps({
        "Device Name": "Test iPhone",
        "Phone Number": "+1 (925) 897-9008",
        "Product Version": "17.5",
        "Last Backup Date": datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
    }))
    (backup_dir / "Manifest.plist").write_bytes(plistlib.dumps({
        "IsEncrypted": False,
        "Lockdown": {"DeviceName": "Test iPhone", "ProductVersion": "17.5"},
    }))
    shutil.rmtree(work)
    return backup_dir


if __name__ == "__main__":
    out = build(Path(__file__).parent / "_built_backup")
    print(f"Wrote {out}")
