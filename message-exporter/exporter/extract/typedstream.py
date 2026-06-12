"""Decode message.attributedBody blobs.

On modern iOS the message text often lives only in `attributedBody`, a
NeXTSTEP typedstream-archived NSAttributedString. We try the pure-Python
`typedstream` parser first and fall back to a byte-level scrape of the
length-prefixed NSString payload when parsing fails.
"""
from __future__ import annotations

import struct

# Inline attachments are represented by the object-replacement character.
OBJECT_REPLACEMENT = "￼"


def decode_attributed_body(blob: bytes | None) -> str | None:
    if not blob:
        return None
    text = _decode_with_typedstream(blob)
    if text is None:
        text = _scrape_nsstring(blob)
    return text


def _decode_with_typedstream(blob: bytes) -> str | None:
    try:
        from typedstream.stream import TypedStreamReader
    except ImportError:
        return None
    try:
        # The NSAttributedString's backing string is the first sizable
        # bytes/str event in the stream.
        for event in TypedStreamReader.from_data(blob):
            if isinstance(event, str):
                return event
            if isinstance(event, bytes):
                return event.decode("utf-8", errors="replace")
    except Exception:
        return None
    return None


def _scrape_nsstring(blob: bytes) -> str | None:
    """Fallback: locate the length-prefixed string after the NSString marker.

    Layout after b"NSString" in a streamtyped blob:
    \\x01\\x94\\x84\\x01\\x2b <len> <utf8 bytes>, where <len> is one byte,
    or \\x81 followed by a little-endian uint16 for longer strings.
    """
    marker = blob.find(b"NSString")
    if marker == -1:
        return None
    pos = marker + len(b"NSString") + 5
    if pos >= len(blob):
        return None
    length = blob[pos]
    pos += 1
    if length == 0x81:
        if pos + 2 > len(blob):
            return None
        length = struct.unpack("<H", blob[pos:pos + 2])[0]
        pos += 2
    elif length == 0x82:
        if pos + 4 > len(blob):
            return None
        length = struct.unpack("<I", blob[pos:pos + 4])[0]
        pos += 4
    end = pos + length
    if end > len(blob):
        return None
    try:
        return blob[pos:end].decode("utf-8", errors="replace")
    except Exception:
        return None
