from exporter.extract.typedstream import decode_attributed_body
from tests.fixtures.make_fixture_smsdb import typedstream_blob


def test_decodes_simple_blob():
    assert decode_attributed_body(typedstream_blob("Hello there")) == "Hello there"


def test_decodes_unicode():
    text = "Café ✨ — naïve"
    assert decode_attributed_body(typedstream_blob(text)) == text


def test_decodes_long_string_two_byte_length():
    text = "x" * 5000
    assert decode_attributed_body(typedstream_blob(text)) == text


def test_garbage_returns_none():
    assert decode_attributed_body(b"\x00\x01garbage-not-a-typedstream") is None


def test_empty_and_null():
    assert decode_attributed_body(None) is None
    assert decode_attributed_body(b"") is None
