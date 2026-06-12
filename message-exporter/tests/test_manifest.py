from exporter.backup import manifest
from exporter.backup.locate import read_backup_info
from tests.fixtures.make_fixture_backup import AB_PATH, DOMAIN, SMS_PATH


def test_resolves_sms_db(fixture_backup):
    path = manifest.resolve_file(fixture_backup, DOMAIN, SMS_PATH)
    assert path is not None and path.exists()
    assert path.parent.name == path.name[:2]   # two-char subdir layout


def test_resolves_addressbook(fixture_backup):
    assert manifest.resolve_file(fixture_backup, DOMAIN, AB_PATH) is not None


def test_missing_file_returns_none(fixture_backup):
    assert manifest.resolve_file(fixture_backup, DOMAIN, "Library/Nope/missing.db") is None


def test_missing_manifest_returns_none(tmp_path):
    assert manifest.resolve_file(tmp_path, DOMAIN, SMS_PATH) is None


def test_read_backup_info(fixture_backup):
    info = read_backup_info(fixture_backup)
    assert info.device_name == "Test iPhone"
    assert info.encrypted is False
    assert info.phone_number == "+1 (925) 897-9008"
    assert info.product_version == "17.5"


def test_read_backup_info_non_backup_dir(tmp_path):
    assert read_backup_info(tmp_path) is None
