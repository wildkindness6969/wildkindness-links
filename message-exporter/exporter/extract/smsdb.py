"""Raw extraction from sms.db (the iMessage/SMS chat database)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RawMessage:
    rowid: int
    guid: str
    text: str | None
    attributed_body: bytes | None
    date: int | float | None
    is_from_me: bool
    service: str
    handle_id: str          # raw handle.id ("" for sent messages)
    chat_rowid: int
    has_attachments: bool


@dataclass
class RawChat:
    rowid: int
    guid: str
    display_name: str | None
    style: int | None
    participants: list[str] = field(default_factory=list)  # raw handle.id values


@dataclass
class ExtractStats:
    total_rows: int = 0
    skipped_system: int = 0     # item_type != 0 (group renames, membership changes)
    skipped_tapbacks: int = 0   # associated_message_type >= 2000


def open_sms_db(path: Path) -> sqlite3.Connection:
    """Open a *copied* sms.db read-only. Never point this at the backup itself."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def fetch_chats(conn: sqlite3.Connection) -> dict[int, RawChat]:
    chats: dict[int, RawChat] = {}
    for row in conn.execute("SELECT ROWID, guid, display_name, style FROM chat"):
        chats[row["ROWID"]] = RawChat(
            rowid=row["ROWID"],
            guid=row["guid"] or f"chat-{row['ROWID']}",
            display_name=row["display_name"] or None,
            style=row["style"],
        )
    for row in conn.execute(
        """SELECT chj.chat_id, h.id AS handle
           FROM chat_handle_join chj JOIN handle h ON h.ROWID = chj.handle_id
           ORDER BY chj.chat_id, h.ROWID"""
    ):
        chat = chats.get(row["chat_id"])
        if chat is not None and row["handle"] not in chat.participants:
            chat.participants.append(row["handle"])
    return chats


def fetch_attachment_summaries(conn: sqlite3.Connection) -> dict[int, list[str]]:
    """message ROWID -> human-readable attachment descriptions."""
    out: dict[int, list[str]] = {}
    cols = table_columns(conn, "attachment")
    if not cols:
        return out
    name_col = "transfer_name" if "transfer_name" in cols else "filename"
    for row in conn.execute(
        f"""SELECT maj.message_id, a.{name_col} AS name, a.mime_type
            FROM message_attachment_join maj
            JOIN attachment a ON a.ROWID = maj.attachment_id"""
    ):
        name = (row["name"] or "attachment").rsplit("/", 1)[-1]
        mime = row["mime_type"] or ""
        kind = "Attachment"
        if mime.startswith("image/"):
            kind = "Image"
        elif mime.startswith("video/"):
            kind = "Video"
        elif mime.startswith("audio/"):
            kind = "Audio"
        out.setdefault(row["message_id"], []).append(f"[{kind}: {name}]")
    return out


def iter_messages(conn: sqlite3.Connection, stats: ExtractStats):
    """Yield RawMessage for every renderable message, skipping system rows
    and tapbacks. Columns are introspected to survive iOS schema drift."""
    cols = table_columns(conn, "message")
    select = [
        "m.ROWID AS rowid", "m.guid AS guid", "m.text AS text",
        "m.date AS date", "m.is_from_me AS is_from_me",
        "h.id AS handle_id", "cmj.chat_id AS chat_rowid",
    ]
    select.append("m.attributedBody AS attributed_body" if "attributedBody" in cols
                  else "NULL AS attributed_body")
    select.append("m.service AS service" if "service" in cols else "NULL AS service")
    select.append("m.cache_has_attachments AS has_attachments"
                  if "cache_has_attachments" in cols else "0 AS has_attachments")
    select.append("m.item_type AS item_type" if "item_type" in cols else "0 AS item_type")
    select.append("m.associated_message_type AS amt"
                  if "associated_message_type" in cols else "0 AS amt")

    sql = f"""
        SELECT {', '.join(select)}
        FROM message m
        JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
        LEFT JOIN handle h ON h.ROWID = m.handle_id
        ORDER BY cmj.chat_id, m.date, m.ROWID
    """
    for row in conn.execute(sql):
        stats.total_rows += 1
        if row["item_type"] not in (0, None):
            stats.skipped_system += 1
            continue
        if (row["amt"] or 0) >= 2000:
            stats.skipped_tapbacks += 1
            continue
        yield RawMessage(
            rowid=row["rowid"],
            guid=row["guid"] or f"msg-{row['rowid']}",
            text=row["text"],
            attributed_body=row["attributed_body"],
            date=row["date"],
            is_from_me=bool(row["is_from_me"]),
            service=row["service"] or "SMS",
            handle_id=row["handle_id"] or "",
            chat_rowid=row["chat_rowid"],
            has_attachments=bool(row["has_attachments"]),
        )
