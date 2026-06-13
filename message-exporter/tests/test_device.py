"""Tests for the libimobiledevice-backed direct-backup path.

The real CLI tools aren't present in CI, so everything here stubs out
subprocess and shutil.which.
"""
import io
import subprocess

import pytest

from exporter.backup import device


# ----------------------------- helpers -------------------------------------

class FakePopen:
    """Minimal stand-in for subprocess.Popen with a scripted stdout."""

    def __init__(self, output: str, returncode: int = 0, on_start=None):
        self.stdout = io.StringIO(output)
        self._returncode = returncode
        if on_start:
            on_start()

    def wait(self):
        return self._returncode


@pytest.fixture
def tools_present(monkeypatch):
    monkeypatch.setattr(device.shutil, "which", lambda name: f"/usr/bin/{name}")


# --------------------------- tool detection --------------------------------

def test_tools_available_true(tools_present):
    assert device.tools_available() is True


def test_tools_available_false(monkeypatch):
    monkeypatch.setattr(device.shutil, "which", lambda name: None)
    assert device.tools_available() is False


def test_require_tools_lists_missing(monkeypatch):
    monkeypatch.setattr(device.shutil, "which", lambda name: None)
    with pytest.raises(device.ToolsNotInstalledError) as exc:
        device.list_devices()
    assert "idevice_id" in str(exc.value)


# ------------------------------ listing ------------------------------------

def test_list_devices_parses_info(tools_present, monkeypatch):
    def fake_run(cmd, **kw):
        out = ""
        if cmd[0] == "idevice_id":
            out = "00008110-AAA\n00008110-BBB\n"
        elif cmd[0] == "ideviceinfo":
            udid, key = cmd[2], cmd[4]
            table = {
                ("00008110-AAA", "DeviceName"): "Jordan's iPhone",
                ("00008110-AAA", "ProductVersion"): "17.5",
                ("00008110-AAA", "PhoneNumber"): "+1 925-555-0000",
                ("00008110-BBB", "DeviceName"): "Old iPhone",
            }
            out = table.get((udid, key), "")
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(device.subprocess, "run", fake_run)
    devices = device.list_devices()
    assert [d.udid for d in devices] == ["00008110-AAA", "00008110-BBB"]
    assert devices[0].name == "Jordan's iPhone"
    assert devices[0].product_version == "17.5"
    assert "iOS 17.5" in devices[0].label
    # Missing keys fall back gracefully.
    assert devices[1].name == "Old iPhone"
    assert devices[1].phone_number is None


def test_list_devices_empty(tools_present, monkeypatch):
    monkeypatch.setattr(
        device.subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""))
    assert device.list_devices() == []


# ------------------------ progress line splitting --------------------------

def test_iter_progress_lines_splits_on_cr_and_lf():
    stream = io.StringIO("Starting\nProgress 10%\rProgress 55%\rDone\n")
    assert list(device._iter_progress_lines(stream)) == [
        "Starting", "Progress 10%", "Progress 55%", "Done"]


# ------------------------------ backup -------------------------------------

def test_backup_device_reports_progress(tools_present, monkeypatch, tmp_path):
    udid = "00008110-AAA"
    output = ("Requesting backup from device...\n"
              "Full backup mode.\n"
              "[=>        ]   5.0%\r"
              "[=====>    ]  50.0%\r"
              "[==========] 100.0%\r"
              "Backup Successful.\n")

    def fake_popen(cmd, **kw):
        return FakePopen(output, returncode=0,
                         on_start=lambda: (tmp_path / udid).mkdir())

    monkeypatch.setattr(device.subprocess, "Popen", fake_popen)

    seen = []
    result = device.backup_device(udid, tmp_path,
                                  progress=lambda d, p: seen.append(p))
    assert result == tmp_path / udid
    fractions = [p for p in seen]
    assert 0.05 in fractions and 0.5 in fractions
    assert fractions[-1] == 1.0           # final "Backup complete." at 100%
    assert fractions == sorted(fractions)  # monotonic


def test_backup_device_trust_error(tools_present, monkeypatch, tmp_path):
    def fake_popen(cmd, **kw):
        return FakePopen("ERROR: Please trust this computer.\n", returncode=255)

    monkeypatch.setattr(device.subprocess, "Popen", fake_popen)
    with pytest.raises(device.DeviceBackupError) as exc:
        device.backup_device("udid", tmp_path)
    assert "Trust This Computer" in str(exc.value)


def test_backup_device_generic_error(tools_present, monkeypatch, tmp_path):
    def fake_popen(cmd, **kw):
        return FakePopen("Some other failure\n", returncode=42)

    monkeypatch.setattr(device.subprocess, "Popen", fake_popen)
    with pytest.raises(device.DeviceBackupError) as exc:
        device.backup_device("udid", tmp_path)
    assert "42" in str(exc.value)


def test_backup_device_missing_folder(tools_present, monkeypatch, tmp_path):
    # Exits 0 but never creates the backup folder.
    def fake_popen(cmd, **kw):
        return FakePopen("Backup Successful.\n", returncode=0)

    monkeypatch.setattr(device.subprocess, "Popen", fake_popen)
    with pytest.raises(device.DeviceBackupError):
        device.backup_device("nope", tmp_path)


# --------------------- pipeline + CLI integration --------------------------

def test_run_export_from_device_discards_backup(monkeypatch, tmp_path, fixture_backup):
    """The backup step is stubbed; verify export runs and discard cleans up."""
    import shutil as _shutil

    from exporter import pipeline

    cache = tmp_path / "cache"
    fake_backup = cache / "udid0001"

    def fake_backup_device(udid, cache_dir, progress=None):
        _shutil.copytree(fixture_backup, fake_backup)
        if progress:
            progress("done", 1.0)
        return fake_backup

    monkeypatch.setattr(device, "backup_device", fake_backup_device)

    result = pipeline.run_export_from_device(
        "udid0001", out_dir=tmp_path / "out", cache_dir=cache,
        discard_backup=True)

    assert result.message_count > 0
    assert (tmp_path / "out").exists()
    assert not fake_backup.exists()        # discarded


def test_run_export_from_device_keeps_backup(monkeypatch, tmp_path, fixture_backup):
    import shutil as _shutil

    from exporter import pipeline

    cache = tmp_path / "cache"
    fake_backup = cache / "udid0001"

    def fake_backup_device(udid, cache_dir, progress=None):
        _shutil.copytree(fixture_backup, fake_backup)
        return fake_backup

    monkeypatch.setattr(device, "backup_device", fake_backup_device)
    pipeline.run_export_from_device("udid0001", out_dir=tmp_path / "out",
                                    cache_dir=cache)
    assert fake_backup.exists()            # retained for incremental reuse


def test_cli_resolve_device_single(monkeypatch):
    import cli
    monkeypatch.setattr(cli, "list_devices",
                        lambda: [device.DeviceInfo(udid="ONLY", name="iPhone")])
    assert cli._resolve_device("") == "ONLY"


def test_cli_resolve_device_ambiguous(monkeypatch, capsys):
    import cli
    monkeypatch.setattr(cli, "list_devices", lambda: [
        device.DeviceInfo(udid="A", name="iPhone A"),
        device.DeviceInfo(udid="B", name="iPhone B")])
    assert cli._resolve_device("") is None      # needs explicit pick
    assert cli._resolve_device("B") == "B"       # explicit pick honoured
    assert cli._resolve_device("Z") is None      # no match
    assert "More than one iPhone" in capsys.readouterr().out


def test_cli_resolve_device_none(monkeypatch):
    import cli
    monkeypatch.setattr(cli, "list_devices", lambda: [])
    assert cli._resolve_device("") is None
