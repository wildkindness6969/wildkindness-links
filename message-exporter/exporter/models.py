"""Normalized in-memory model.

Every exporter (PDF, Excel, and the future Converse AI roster/JSONL
exporters) consumes only these dataclasses, never raw sms.db rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Contact:
    handle: str            # normalized number ("+19255551234") or lowercased email
    name: str | None       # resolved contact name, if any
    raw_handle: str = ""   # handle.id exactly as stored in sms.db

    @property
    def display(self) -> str:
        return self.name or pretty_handle(self.handle)


@dataclass
class Message:
    guid: str
    conversation_id: str        # chat.guid (stable thread id)
    timestamp: datetime         # timezone-aware, local time
    is_from_me: bool
    sender_handle: str          # normalized handle ("" for sent messages)
    sender_name: str            # resolved contact name or formatted number
    text: str                   # from `text` or decoded attributedBody
    service: str                # "iMessage" | "SMS" | "RCS" | ...
    has_attachments: bool = False
    attachment_summary: str = ""   # e.g. "[Image: IMG_1234.heic]"


@dataclass
class Conversation:
    conversation_id: str        # chat.guid
    chat_rowid: int
    display_name: str           # contact/group name or joined participant names
    participants: list[Contact] = field(default_factory=list)
    is_group: bool = False
    messages: list[Message] = field(default_factory=list)  # ascending by timestamp

    @property
    def sent_count(self) -> int:
        return sum(1 for m in self.messages if m.is_from_me)

    @property
    def received_count(self) -> int:
        return len(self.messages) - self.sent_count

    @property
    def first_timestamp(self) -> datetime | None:
        return self.messages[0].timestamp if self.messages else None

    @property
    def last_timestamp(self) -> datetime | None:
        return self.messages[-1].timestamp if self.messages else None


@dataclass
class ExportBundle:
    conversations: list[Conversation]
    owner_number: str
    device_name: str
    export_date: datetime
    warnings: list[str] = field(default_factory=list)

    @property
    def total_messages(self) -> int:
        return sum(len(c.messages) for c in self.conversations)


def pretty_handle(handle: str) -> str:
    """Format '+19258979008' as '(925) 897-9008'; pass other handles through."""
    if handle.startswith("+1") and len(handle) == 12 and handle[1:].isdigit():
        d = handle[2:]
        return f"({d[:3]}) {d[3:6]}-{d[6:]}"
    return handle
