"""Find iPhone backups on this computer and read their metadata."""
from __future__ import annotations

import plistlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..config import MOBILESYNC_CANDIDATES


@dataclass
class BackupInfo:
    path: Path
    udid: str
    device_name: str
    phone_number: str | None
    last_backup_date: datetime | None
    product_version: str | None     # iOS version
    encrypted: bool
    size_bytes: int

    @property
    def size_display(self) -> str:
        size = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024
        return f"{size:.1f} TB"


class FullDiskAccessError(PermissionError):
    """macOS blocked us from reading the MobileSync folder."""


def default_backup_roots() -> list[Path]:
    return [p for p in MOBILESYNC_CANDIDATES if p.exists()]


def list_backups(roots: list[Path] | None = None) -> list[BackupInfo]:
    """Scan backup roots, newest backup first."""
    if roots is None:
        roots = default_backup_roots()
    backups: list[BackupInfo] = []
    for root in roots:
        try:
            children = sorted(root.iterdir())
        except PermissionError as exc:
            raise FullDiskAccessError(str(root)) from exc
        for child in children:
            if child.is_dir():
                info = read_backup_info(child)
                if info:
                    backups.append(info)
    backups.sort(key=lambda b: b.last_backup_date or datetime.min, reverse=True)
    return backups


def read_backup_info(backup_dir: Path) -> BackupInfo | None:
    """Read Info.plist/Manifest.plist; returns None if this isn't a backup dir."""
    backup_dir = Path(backup_dir)
    info_plist = backup_dir / "Info.plist"
    manifest_plist = backup_dir / "Manifest.plist"
    if not manifest_plist.exists() and not (backup_dir / "Manifest.db").exists():
        return None

    info: dict = {}
    if info_plist.exists():
        try:
            info = plistlib.loads(info_plist.read_bytes())
        except Exception:
            info = {}
    manifest: dict = {}
    if manifest_plist.exists():
        try:
            manifest = plistlib.loads(manifest_plist.read_bytes())
        except Exception:
            manifest = {}

    last_date = info.get("Last Backup Date")
    if last_date is not None and not isinstance(last_date, datetime):
        last_date = None

    return BackupInfo(
        path=backup_dir,
        udid=backup_dir.name,
        device_name=info.get("Device Name")
        or manifest.get("Lockdown", {}).get("DeviceName")
        or backup_dir.name,
        phone_number=info.get("Phone Number"),
        last_backup_date=last_date,
        product_version=info.get("Product Version")
        or manifest.get("Lockdown", {}).get("ProductVersion"),
        encrypted=bool(manifest.get("IsEncrypted", False)),
        size_bytes=_dir_size(backup_dir),
    )


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except OSError:
                continue
    except OSError:
        pass
    return total
