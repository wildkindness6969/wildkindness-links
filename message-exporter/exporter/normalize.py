"""Stage C: turn raw sms.db rows + contact names into the ExportBundle model."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from .config import OWNER_NUMBER
from .extract import smsdb
from .extract.contacts import load_contact_names, lookup_name
from .extract.timestamps import cocoa_to_datetime
from .extract.typedstream import OBJECT_REPLACEMENT, decode_attributed_body
from .models import Contact, Conversation, ExportBundle, Message, pretty_handle
from .phonenumbers_util import normalize_handle

GROUP_CHAT_STYLE = 43

ProgressFn = Callable[[str, float], None]


def build_bundle(
    sms_db_path: Path,
    addressbook_path: Path | None = None,
    device_name: str = "iPhone",
    owner_number: str = OWNER_NUMBER,
    progress: ProgressFn | None = None,
) -> ExportBundle:
    def report(detail: str, pct: float) -> None:
        if progress:
            progress(detail, pct)

    report("Reading contacts…", 0.0)
    names = load_contact_names(addressbook_path)

    conn = smsdb.open_sms_db(sms_db_path)
    try:
        report("Reading conversations…", 0.05)
        raw_chats = smsdb.fetch_chats(conn)
        attachments = smsdb.fetch_attachment_summaries(conn)

        conversations: dict[int, Conversation] = {}
        for rowid, raw in raw_chats.items():
            participants = []
            for raw_handle in raw.participants:
                handle = normalize_handle(raw_handle)
                participants.append(Contact(
                    handle=handle,
                    name=lookup_name(names, handle),
                    raw_handle=raw_handle,
                ))
            is_group = raw.style == GROUP_CHAT_STYLE or len(participants) > 1
            conversations[rowid] = Conversation(
                conversation_id=raw.guid,
                chat_rowid=rowid,
                display_name=_conversation_name(raw.display_name, participants, is_group),
                participants=participants,
                is_group=is_group,
            )

        report("Reading messages…", 0.1)
        stats = smsdb.ExtractStats()
        decode_failures = 0
        empty_skipped = 0
        for raw_msg in smsdb.iter_messages(conn, stats):
            convo = conversations.get(raw_msg.chat_rowid)
            if convo is None:
                continue
            attachment_summary = " ".join(attachments.get(raw_msg.rowid, []))
            text, failed = _resolve_body(raw_msg, attachment_summary)
            if failed:
                decode_failures += 1
            if not text:
                empty_skipped += 1
                continue
            timestamp = cocoa_to_datetime(raw_msg.date)
            if timestamp is None:
                empty_skipped += 1
                continue
            sender_handle = normalize_handle(raw_msg.handle_id)
            if raw_msg.is_from_me:
                sender_name = "Me"
            else:
                sender_name = (lookup_name(names, sender_handle)
                               or pretty_handle(sender_handle))
            convo.messages.append(Message(
                guid=raw_msg.guid,
                conversation_id=convo.conversation_id,
                timestamp=timestamp,
                is_from_me=raw_msg.is_from_me,
                sender_handle=sender_handle,
                sender_name=sender_name,
                text=text,
                service=raw_msg.service,
                has_attachments=raw_msg.has_attachments,
                attachment_summary=attachment_summary,
            ))
            if stats.total_rows % 2000 == 0:
                report(f"Reading messages… ({stats.total_rows:,} rows)", 0.1)
    finally:
        conn.close()

    result = [c for c in conversations.values() if c.messages]
    for convo in result:
        convo.messages.sort(key=lambda m: m.timestamp)
    result.sort(key=lambda c: c.last_timestamp or datetime.min.astimezone(),
                reverse=True)

    warnings = []
    if decode_failures:
        warnings.append(f"{decode_failures} message(s) could not be fully decoded "
                        "and are shown as placeholders.")
    if stats.skipped_tapbacks:
        warnings.append(f"{stats.skipped_tapbacks} reaction(s) (likes/loves) were skipped.")
    if stats.skipped_system:
        warnings.append(f"{stats.skipped_system} system event(s) "
                        "(group renames etc.) were skipped.")
    if empty_skipped:
        warnings.append(f"{empty_skipped} empty/undated row(s) were skipped.")

    report("Messages loaded.", 0.3)
    return ExportBundle(
        conversations=result,
        owner_number=owner_number,
        device_name=device_name,
        export_date=datetime.now().astimezone(),
        warnings=warnings,
    )


def _resolve_body(raw_msg: smsdb.RawMessage, attachment_summary: str) -> tuple[str, bool]:
    """Returns (body text, decode_failed). Empty body means 'skip this row'."""
    text = raw_msg.text
    failed = False
    if not text and raw_msg.attributed_body:
        text = decode_attributed_body(raw_msg.attributed_body)
        if text is None:
            failed = True
            text = "[Unable to decode message body]"
    text = (text or "").replace(OBJECT_REPLACEMENT, "").strip()
    if not text and attachment_summary:
        text = attachment_summary
    return text, failed


def _conversation_name(chat_display_name: str | None,
                       participants: list[Contact],
                       is_group: bool) -> str:
    if chat_display_name:
        return chat_display_name
    if not participants:
        return "Unknown"
    if is_group:
        return ", ".join(p.display for p in participants)
    return participants[0].display
