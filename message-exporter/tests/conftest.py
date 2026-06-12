import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.fixtures import make_fixture_backup, make_fixture_smsdb  # noqa: E402


@pytest.fixture(scope="session")
def sms_db(tmp_path_factory) -> Path:
    return make_fixture_smsdb.build(tmp_path_factory.mktemp("smsdb") / "sms.db")


@pytest.fixture(scope="session")
def fixture_backup(tmp_path_factory) -> Path:
    return make_fixture_backup.build(tmp_path_factory.mktemp("backup") / "udid0001")


@pytest.fixture(scope="session")
def bundle(fixture_backup):
    from exporter.backup.decrypt import open_backup
    from exporter.normalize import build_bundle

    with open_backup(fixture_backup) as reader:
        return build_bundle(reader.get_sms_db(), reader.get_addressbook_db(),
                            device_name="Test iPhone")
