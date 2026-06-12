from datetime import datetime, timezone

from exporter.extract.timestamps import cocoa_to_datetime


def test_nanoseconds_ios11_plus():
    # 2025-03-04 17:30:00 UTC in ns since 2001-01-01
    ns = int((datetime(2025, 3, 4, 17, 30, tzinfo=timezone.utc)
              - datetime(2001, 1, 1, tzinfo=timezone.utc)).total_seconds() * 1e9)
    dt = cocoa_to_datetime(ns)
    assert dt.astimezone(timezone.utc) == datetime(2025, 3, 4, 17, 30, tzinfo=timezone.utc)


def test_legacy_seconds():
    s = int((datetime(2024, 11, 1, 8, 0, tzinfo=timezone.utc)
             - datetime(2001, 1, 1, tzinfo=timezone.utc)).total_seconds())
    dt = cocoa_to_datetime(s)
    assert dt.astimezone(timezone.utc) == datetime(2024, 11, 1, 8, 0, tzinfo=timezone.utc)


def test_null_and_zero():
    assert cocoa_to_datetime(None) is None
    assert cocoa_to_datetime(0) is None


def test_result_is_timezone_aware():
    assert cocoa_to_datetime(700_000_000).tzinfo is not None
