"""Convert Apple Cocoa-epoch timestamps to timezone-aware datetimes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)

# Values above this are nanoseconds since 2001 (iOS 11+); below, seconds.
_NS_THRESHOLD = 1_000_000_000_000


def cocoa_to_datetime(value: int | float | None) -> datetime | None:
    if not value:
        return None
    if value > _NS_THRESHOLD:
        value = value / 1_000_000_000
    return (APPLE_EPOCH + timedelta(seconds=value)).astimezone()
