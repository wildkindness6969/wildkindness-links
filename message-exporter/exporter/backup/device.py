"""Make a backup directly from a plugged-in iPhone via libimobiledevice.

This drives the same backup protocol Finder uses (mobilebackup2), but from
the command line, so the app can trigger the backup itself and then extract
only the message database. Two things worth knowing:

* The *first* backup is the slow one. idevicebackup2 backs up incrementally,
  so as long as the backup directory is kept around (see DEFAULT_BACKUP_CACHE),
  every later run only transfers what changed — usually seconds of messages
  rather than another full pass.
* There is no way to ask the phone for *only* the message database. The device
  decides what a backup contains. We can, however, throw the rest away after
  extracting what we need (see ``run_export_from_device(discard_backup=True)``).

All of this requires the libimobiledevice command-line tools (`idevice_id`,
`ideviceinfo`, `idevicebackup2`) to be installed. On macOS: `brew install
libimobiledevice`.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

ProgressFn = Callable[[str, float], None]

_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_TOOLS = ("idevice_id", "ideviceinfo", "idevicebackup2")


class DeviceError(RuntimeError):
    """Base for any failure talking to a connected iPhone."""


class ToolsNotInstalledError(DeviceError):
    """The libimobiledevice CLI tools aren't on PATH."""


class NoDeviceError(DeviceError):
    """No trusted iPhone is currently connected."""


class DeviceBackupError(DeviceError):
    """idevicebackup2 exited with an error."""


@dataclass
class DeviceInfo:
    udid: str
    name: str
    product_version: str | None = None     # iOS version
    phone_number: str | None = None

    @property
    def label(self) -> str:
        bits = [self.name]
        if self.product_version:
            bits.append(f"iOS {self.product_version}")
        if self.phone_number:
            bits.append(self.phone_number)
        return " · ".join(bits)


def tools_available() -> bool:
    """True if the libimobiledevice CLI tools are installed."""
    return all(shutil.which(tool) for tool in _TOOLS)


def _require_tools() -> None:
    missing = [t for t in _TOOLS if not shutil.which(t)]
    if missing:
        raise ToolsNotInstalledError(
            "The libimobiledevice tools are needed to back up directly from a "
            "phone (missing: " + ", ".join(missing) + "). On macOS install them "
            "with:  brew install libimobiledevice"
        )


def _run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def list_devices() -> list[DeviceInfo]:
    """Every trusted iPhone connected over USB, with its name and iOS version."""
    _require_tools()
    proc = _run(["idevice_id", "-l"])
    udids = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    devices: list[DeviceInfo] = []
    for udid in udids:
        devices.append(DeviceInfo(udid=udid, name=_device_name(udid),
                                  product_version=_device_key(udid, "ProductVersion"),
                                  phone_number=_device_key(udid, "PhoneNumber")))
    return devices


def _device_name(udid: str) -> str:
    return _device_key(udid, "DeviceName") or "iPhone"


def _device_key(udid: str, key: str) -> str | None:
    try:
        proc = _run(["ideviceinfo", "-u", udid, "-k", key])
    except Exception:
        return None
    value = proc.stdout.strip()
    return value or None


def _iter_progress_lines(stream) -> Iterator[str]:
    """Yield logical lines, treating both \\n and \\r as breaks.

    idevicebackup2 redraws its progress bar with carriage returns, so a plain
    readline() would block until the whole backup finished. Reading a chunk at
    a time and splitting on either terminator lets progress flow through live.
    """
    buf = ""
    while True:
        chunk = stream.read(256)
        if not chunk:
            break
        buf += chunk
        parts = re.split(r"[\r\n]", buf)
        buf = parts.pop()
        for part in parts:
            if part:
                yield part
    if buf:
        yield buf


def backup_device(
    udid: str,
    cache_dir: Path,
    progress: ProgressFn | None = None,
) -> Path:
    """Back up ``udid`` into ``cache_dir`` and return the backup folder.

    Incremental: if a backup for this device already exists under ``cache_dir``
    it is reused and only changes are fetched. Returns ``cache_dir/<udid>``.
    """
    _require_tools()
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    def report(detail: str, pct: float) -> None:
        if progress:
            progress(detail, pct)

    report("Starting backup…", 0.0)
    proc = subprocess.Popen(
        ["idevicebackup2", "-u", udid, "backup", str(cache_dir)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    last_line = ""
    seen_progress = False
    assert proc.stdout is not None
    for line in _iter_progress_lines(proc.stdout):
        last_line = line.strip()
        if not last_line:
            continue
        match = _PERCENT_RE.search(last_line)
        if match:
            seen_progress = True
            report("Backing up your iPhone…", float(match.group(1)) / 100.0)
        elif not seen_progress:
            # Pre-transfer chatter ("Requesting backup…", negotiating protocol).
            report(last_line, 0.0)
    code = proc.wait()
    if code != 0:
        raise _backup_error(last_line, code)

    backup_dir = cache_dir / udid
    if not backup_dir.exists():
        raise DeviceBackupError(
            "The backup finished but no backup folder was created at "
            f"{backup_dir}. Check that the iPhone stayed connected.")
    report("Backup complete.", 1.0)
    return backup_dir


def _backup_error(last_line: str, code: int) -> DeviceBackupError:
    text = last_line.lower()
    if "trust" in text or "pair" in text or "not paired" in text:
        return DeviceBackupError(
            "The iPhone hasn't trusted this computer yet. Unlock the phone, "
            "tap 'Trust This Computer', enter your passcode, then try again.")
    if "no device" in text or "no such device" in text:
        return DeviceBackupError(
            "No iPhone was found. Plug it in with a cable and unlock it.")
    detail = f" ({last_line})" if last_line else ""
    return DeviceBackupError(f"The backup failed{detail}. Exit code {code}.")
