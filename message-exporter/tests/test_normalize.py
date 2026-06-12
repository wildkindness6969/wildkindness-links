def conversations_by_name(bundle):
    return {c.display_name: c for c in bundle.conversations}


def test_conversation_count(bundle):
    assert len(bundle.conversations) == 4


def test_contact_name_resolution(bundle):
    names = conversations_by_name(bundle)
    assert "Alice Client" in names          # matched via address book
    assert "Bob Vendor" in names            # matched despite formatting differences
    assert "Wedding Crew" in names          # group display_name wins


def test_group_detection(bundle):
    names = conversations_by_name(bundle)
    assert names["Wedding Crew"].is_group
    assert not names["Alice Client"].is_group
    # Unnamed group falls back to joined participant names.
    unnamed = [c for c in bundle.conversations
               if c.is_group and c.display_name != "Wedding Crew"]
    assert len(unnamed) == 1
    assert "Bob Vendor" in unnamed[0].display_name


def test_alice_thread_contents(bundle):
    alice = conversations_by_name(bundle)["Alice Client"]
    texts = [m.text for m in alice.messages]
    # plain text rows
    assert texts[0].startswith("Hi! Do you have any goldendoodle")
    # attributedBody-only rows decoded
    assert "Can we visit Saturday?" in texts[2]
    assert "10am works great" in texts[3]
    # attachment-only message becomes the attachment summary
    assert any("IMG_1234.heic" in t for t in texts)
    # corrupted blob becomes a placeholder
    assert "[Unable to decode message body]" in texts
    # tapback row was skipped entirely
    assert not any("Loved an image" in t for t in texts)


def test_messages_sorted_and_directional(bundle):
    alice = conversations_by_name(bundle)["Alice Client"]
    stamps = [m.timestamp for m in alice.messages]
    assert stamps == sorted(stamps)
    assert alice.messages[0].is_from_me is False
    assert alice.messages[1].is_from_me is True
    assert alice.messages[1].sender_name == "Me"


def test_legacy_seconds_timestamps(bundle):
    bob = conversations_by_name(bundle)["Bob Vendor"]
    assert bob.messages[0].timestamp.year == 2024


def test_system_and_empty_rows_skipped(bundle):
    wedding = conversations_by_name(bundle)["Wedding Crew"]
    assert len(wedding.messages) == 3      # rename event excluded
    assert bundle.total_messages == 12     # 15 rows - tapback - system - empty


def test_warnings_reported(bundle):
    joined = " ".join(bundle.warnings)
    assert "could not be fully decoded" in joined
    assert "reaction" in joined
    assert "system event" in joined


def test_unknown_number_pretty_formatted(bundle):
    wedding = conversations_by_name(bundle)["Wedding Crew"]
    senders = {m.sender_name for m in wedding.messages if not m.is_from_me}
    assert "(999) 888-7777" in senders     # unknown handle, formatted not raw
    assert "Carol Cakes LLC" in senders    # org-only contact via email
