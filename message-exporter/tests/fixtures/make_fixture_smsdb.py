"""Build a synthetic sms.db replicating the real iOS chat-database schema,
seeded with edge cases. Used by tests and `cli.py --sms-db` smoke runs."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


def ns(year, month, day, hour=12, minute=0, second=0) -> int:
    dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    return int((dt - APPLE_EPOCH).total_seconds() * 1_000_000_000)


def secs(year, month, day, hour=12, minute=0, second=0) -> int:
    dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    return int((dt - APPLE_EPOCH).total_seconds())


def typedstream_blob(text: str) -> bytes:
    """Minimal streamtyped blob the fallback scraper (and real parsers'
    error paths) can extract: NSString marker + length-prefixed UTF-8."""
    payload = text.encode("utf-8")
    if len(payload) < 0x80:
        length = bytes([len(payload)])
    else:
        length = b"\x81" + len(payload).to_bytes(2, "little")
    return (b"\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84"
            b"NSString\x01\x94\x84\x01+" + length + payload)


# Handles: two contacts in the fixture address book, one unknown number,
# and an email handle.
HANDLES = [
    (1, "+19255551234", "iMessage"),   # Alice Client (in address book)
    (2, "(415) 555-9876", "SMS"),      # Bob Vendor, non-normalized form in db
    (3, "+19998887777", "iMessage"),   # unknown number
    (4, "carol@example.com", "iMessage"),
]

CHATS = [
    # (rowid, guid, display_name, style)
    (1, "iMessage;-;+19255551234", None, 45),            # 1:1 with Alice
    (2, "SMS;-;+14155559876", None, 45),                  # 1:1 with Bob
    (3, "iMessage;+;chat123", "Wedding Crew", 43),        # named group
    (4, "iMessage;+;chat456", None, 43),                  # unnamed group
]

CHAT_HANDLES = [(1, 1), (2, 2), (3, 1), (3, 3), (3, 4), (4, 2), (4, 3)]


def build(path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE handle (
            ROWID INTEGER PRIMARY KEY, id TEXT, country TEXT,
            service TEXT, uncanonicalized_id TEXT
        );
        CREATE TABLE chat (
            ROWID INTEGER PRIMARY KEY, guid TEXT, style INTEGER,
            chat_identifier TEXT, service_name TEXT, display_name TEXT
        );
        CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT,
            attributedBody BLOB, handle_id INTEGER, service TEXT,
            date INTEGER, is_from_me INTEGER, item_type INTEGER DEFAULT 0,
            associated_message_type INTEGER DEFAULT 0,
            cache_has_attachments INTEGER DEFAULT 0
        );
        CREATE TABLE chat_message_join (
            chat_id INTEGER, message_id INTEGER, message_date INTEGER
        );
        CREATE TABLE chat_handle_join (chat_id INTEGER, handle_id INTEGER);
        CREATE TABLE attachment (
            ROWID INTEGER PRIMARY KEY, guid TEXT, filename TEXT,
            mime_type TEXT, transfer_name TEXT, total_bytes INTEGER
        );
        CREATE TABLE message_attachment_join (
            message_id INTEGER, attachment_id INTEGER
        );
    """)
    c.executemany("INSERT INTO handle (ROWID, id, service) VALUES (?, ?, ?)", HANDLES)
    c.executemany("INSERT INTO chat (ROWID, guid, display_name, style) VALUES (?, ?, ?, ?)",
                  [(r, g, d, s) for r, g, d, s in CHATS])
    c.executemany("INSERT INTO chat_handle_join (chat_id, handle_id) VALUES (?, ?)",
                  CHAT_HANDLES)

    messages = [
        # (rowid, guid, text, attributedBody, handle_id, service, date,
        #  is_from_me, item_type, assoc_type, has_attach, chat_id)
        # --- chat 1 (Alice): plain text both directions, multi-day ---
        (1, "g1", "Hi! Do you have any goldendoodle puppies available?",
         None, 1, "iMessage", ns(2025, 3, 4, 17, 30), 0, 0, 0, 0, 1),
        (2, "g2", "Hi Alice! Yes, we have two boys from the spring litter \U0001F436",
         None, 0, "iMessage", ns(2025, 3, 4, 17, 42), 1, 0, 0, 0, 1),
        # NULL text, body only in attributedBody (modern iOS)
        (3, "g3", None, typedstream_blob("That's wonderful! Can we visit Saturday?"),
         1, "iMessage", ns(2025, 3, 5, 9, 15), 0, 0, 0, 0, 1),
        (4, "g4", None, typedstream_blob("Absolutely — 10am works great."),
         0, "iMessage", ns(2025, 3, 5, 9, 20), 1, 0, 0, 0, 1),
        # attachment-only message (object-replacement char body)
        (5, "g5", "￼", None, 1, "iMessage", ns(2025, 3, 6, 14, 0), 0, 0, 0, 1, 1),
        # tapback — must be skipped
        (6, "g6", "Loved an image", None, 1, "iMessage",
         ns(2025, 3, 6, 14, 5), 0, 0, 2001, 0, 1),
        # corrupted attributedBody — placeholder + decode-failure count
        (7, "g7", None, b"\x00\x01garbage-not-a-typedstream", 1, "iMessage",
         ns(2025, 3, 6, 15, 0), 0, 0, 0, 0, 1),
        # --- chat 2 (Bob): SMS, legacy seconds timestamps ---
        (8, "g8", "Invoice for the fencing attached", None, 2, "SMS",
         secs(2024, 11, 1, 8, 0), 0, 0, 0, 0, 2),
        (9, "g9", "Got it, thanks Bob!", None, 0, "SMS",
         secs(2024, 11, 1, 8, 30), 1, 0, 0, 0, 2),
        # --- chat 3 (named group): sender labels, system row skipped ---
        (10, "g10", "Who's bringing the cake?", None, 3, "iMessage",
         ns(2025, 5, 10, 18, 0), 0, 0, 0, 0, 3),
        (11, "g11", "I can! \U0001F382", None, 4, "iMessage",
         ns(2025, 5, 10, 18, 5), 0, 0, 0, 0, 3),
        (12, "g12", "You're the best, Carol", None, 0, "iMessage",
         ns(2025, 5, 10, 18, 6), 1, 0, 0, 0, 3),
        # group-rename system event — must be skipped
        (13, "g13", None, None, 3, "iMessage", ns(2025, 5, 10, 18, 7), 0, 2, 0, 0, 3),
        # --- chat 4 (unnamed group): very long body for bubble splitting ---
        (14, "g14", ("Here are the full care instructions. " * 200).strip(),
         None, 3, "iMessage", ns(2025, 6, 1, 12, 0), 0, 0, 0, 0, 4),
        # empty row (no text, no body, no attachment) — must be skipped
        (15, "g15", None, None, 2, "SMS", ns(2025, 6, 1, 12, 5), 0, 0, 0, 0, 4),
    ]
    c.executemany(
        """INSERT INTO message (ROWID, guid, text, attributedBody, handle_id,
           service, date, is_from_me, item_type, associated_message_type,
           cache_has_attachments) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [m[:11] for m in messages])
    c.executemany("INSERT INTO chat_message_join (chat_id, message_id) VALUES (?, ?)",
                  [(m[11], m[0]) for m in messages])

    c.execute("""INSERT INTO attachment (ROWID, guid, filename, mime_type,
                 transfer_name, total_bytes)
                 VALUES (1, 'a1', '~/Library/SMS/Attachments/ab/IMG_1234.heic',
                         'image/heic', 'IMG_1234.heic', 123456)""")
    c.execute("INSERT INTO message_attachment_join (message_id, attachment_id) VALUES (5, 1)")
    conn.commit()
    conn.close()
    return path


if __name__ == "__main__":
    out = build(Path(__file__).parent / "_built" / "sms.db")
    print(f"Wrote {out}")
