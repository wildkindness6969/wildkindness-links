"""End-to-end orchestration: backup dir (or bare sms.db) -> PDFs + Excel."""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from .backup.decrypt import open_backup
from .backup.locate import read_backup_info
from .config import DEFAULT_BACKUP_CACHE, DEFAULT_OUTPUT_ROOT, OWNER_NUMBER
from .exporters import ALL_EXPORTERS
from .models import ExportBundle
from .normalize import build_bundle

ProgressFn = Callable[[str, float], None]


@dataclass
class ExportResult:
    out_dir: Path
    outputs: list[Path] = field(default_factory=list)
    conversation_count: int = 0
    message_count: int = 0
    warnings: list[str] = field(default_factory=list)


def default_out_dir(device_name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in device_name).strip() or "iPhone"
    stamp = datetime.now().strftime("%Y-%m-%d")
    return DEFAULT_OUTPUT_ROOT / f"{safe}-{stamp}"


def run_export_from_backup(
    backup_dir: Path,
    password: str | None = None,
    out_dir: Path | None = None,
    progress: ProgressFn | None = None,
) -> ExportResult:
    def report(detail: str, pct: float) -> None:
        if progress:
            progress(detail, pct)

    info = read_backup_info(backup_dir)
    device_name = info.device_name if info else "iPhone"
    owner = (info.phone_number if info and info.phone_number else OWNER_NUMBER)
    if out_dir is None:
        out_dir = default_out_dir(device_name)

    report("Opening backup…", 0.01)
    with open_backup(Path(backup_dir), password) as reader:
        report("Extracting message database…", 0.05)
        sms_db = reader.get_sms_db()
        if sms_db is None:
            raise RuntimeError(
                "No message database was found in this backup. "
                "Make sure the backup completed successfully in Finder.")
        report("Extracting contacts…", 0.12)
        addressbook = reader.get_addressbook_db()

        bundle = build_bundle(
            sms_db, addressbook,
            device_name=device_name, owner_number=owner,
            progress=lambda d, p: report(d, 0.15 + p * 0.5),
        )
        return run_exporters(bundle, Path(out_dir), progress)


def run_export_from_device(
    udid: str,
    password: str | None = None,
    out_dir: Path | None = None,
    cache_dir: Path | None = None,
    discard_backup: bool = False,
    progress: ProgressFn | None = None,
) -> ExportResult:
    """Back up a connected iPhone, then export its messages.

    The backup is the slow part, so it owns the first 60% of the progress bar.
    By default the backup is kept under ``cache_dir`` so the next run is a fast
    incremental delta; pass ``discard_backup=True`` to delete it afterwards and
    reclaim the disk space (at the cost of a full backup next time).
    """
    from .backup.device import backup_device

    if cache_dir is None:
        cache_dir = DEFAULT_BACKUP_CACHE

    def report(detail: str, pct: float) -> None:
        if progress:
            progress(detail, pct)

    backup_dir = backup_device(
        udid, Path(cache_dir),
        progress=lambda d, p: report(d, p * 0.6),
    )
    try:
        return run_export_from_backup(
            backup_dir, password, out_dir,
            progress=lambda d, p: report(d, 0.6 + p * 0.4),
        )
    finally:
        if discard_backup:
            shutil.rmtree(backup_dir, ignore_errors=True)


def run_export_from_sms_db(
    sms_db: Path,
    addressbook: Path | None = None,
    out_dir: Path | None = None,
    progress: ProgressFn | None = None,
) -> ExportResult:
    bundle = build_bundle(sms_db, addressbook, progress=progress)
    if out_dir is None:
        out_dir = default_out_dir(bundle.device_name)
    return run_exporters(bundle, Path(out_dir), progress)


def run_exporters(bundle: ExportBundle, out_dir: Path,
                  progress: ProgressFn | None = None) -> ExportResult:
    def report(detail: str, pct: float) -> None:
        if progress:
            progress(detail, pct)

    out_dir.mkdir(parents=True, exist_ok=True)
    result = ExportResult(
        out_dir=out_dir,
        conversation_count=len(bundle.conversations),
        message_count=bundle.total_messages,
    )
    n = len(ALL_EXPORTERS)
    for i, exporter_cls in enumerate(ALL_EXPORTERS):
        exporter = exporter_cls()
        base, span = 0.5 + 0.45 * (i / n), 0.45 / n
        result.outputs.extend(exporter.export(
            bundle, out_dir,
            progress=lambda d, p, b=base, s=span: report(d, b + p * s),
        ))
    result.warnings = list(bundle.warnings)
    _write_log(result, bundle)
    report("Done.", 1.0)
    return result


def _write_log(result: ExportResult, bundle: ExportBundle) -> None:
    log = result.out_dir / "export_log.txt"
    lines = [
        f"Export finished {bundle.export_date.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Device: {bundle.device_name}",
        f"Owner number: {bundle.owner_number}",
        f"Conversations: {result.conversation_count}",
        f"Messages: {result.message_count}",
        "",
        "Files:",
        *(f"  {p}" for p in result.outputs),
    ]
    if result.warnings:
        lines += ["", "Notes:"] + [f"  - {w}" for w in result.warnings]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result.outputs.append(log)
