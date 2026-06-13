#!/usr/bin/env python3
"""Command-line entry point (the web UI in app.py is the friendlier path).

Examples:
    python cli.py --list
    python cli.py --list-devices
    python cli.py --device                       # back up the connected iPhone, then export
    python cli.py --device <udid> --discard-backup
    python cli.py --backup ~/Library/.../Backup/<udid> --out ~/Documents/MessageExports/x
    python cli.py --sms-db tests/fixtures/_built/sms.db --out /tmp/x
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from exporter.backup.decrypt import WrongPasswordError
from exporter.backup.device import DeviceError, list_devices
from exporter.backup.locate import FullDiskAccessError, list_backups, read_backup_info
from exporter.pipeline import (run_export_from_backup, run_export_from_device,
                               run_export_from_sms_db)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export iPhone messages to PDF + Excel.")
    parser.add_argument("--list", action="store_true", help="List backups found on this computer")
    parser.add_argument("--list-devices", action="store_true",
                        help="List iPhones connected over USB")
    parser.add_argument("--device", nargs="?", const="", metavar="UDID",
                        help="Back up the connected iPhone, then export (give a "
                             "UDID to pick one when several are plugged in)")
    parser.add_argument("--discard-backup", action="store_true",
                        help="With --device: delete the backup after exporting "
                             "(next run will be a full backup again)")
    parser.add_argument("--cache-dir", type=Path,
                        help="With --device: where to keep the backup between runs")
    parser.add_argument("--backup", type=Path, help="Path to an iPhone backup folder")
    parser.add_argument("--sms-db", type=Path, help="Path to a bare sms.db (testing)")
    parser.add_argument("--addressbook", type=Path, help="Optional AddressBook.sqlitedb (with --sms-db)")
    parser.add_argument("--out", type=Path, help="Output folder (default: ~/Documents/MessageExports/...)")
    parser.add_argument("--password", help="Backup password (prompted if needed and omitted)")
    args = parser.parse_args()

    def progress(detail: str, pct: float) -> None:
        print(f"[{pct * 100:5.1f}%] {detail}")

    try:
        if args.list:
            backups = list_backups()
            if not backups:
                print("No iPhone backups found. Plug in your iPhone, open Finder, "
                      "select it in the sidebar, and click 'Back Up Now'.")
                return 1
            for b in backups:
                lock = "encrypted" if b.encrypted else "not encrypted"
                when = b.last_backup_date.strftime("%Y-%m-%d %H:%M") if b.last_backup_date else "unknown date"
                print(f"{b.device_name}  ({when}, {b.size_display}, {lock})\n  {b.path}")
            return 0

        if args.list_devices:
            return _list_devices()

        if args.sms_db:
            result = run_export_from_sms_db(args.sms_db, args.addressbook,
                                            args.out, progress)
        elif args.device is not None:
            udid = _resolve_device(args.device)
            if udid is None:
                return 1
            result = run_export_from_device(
                udid, password=args.password, out_dir=args.out,
                cache_dir=args.cache_dir, discard_backup=args.discard_backup,
                progress=progress)
        elif args.backup:
            password = args.password
            info = read_backup_info(args.backup)
            if info and info.encrypted and not password:
                password = getpass.getpass("Backup password: ")
            result = run_export_from_backup(args.backup, password, args.out, progress)
        else:
            parser.print_help()
            return 2
    except FullDiskAccessError:
        print("\nmacOS blocked access to the backups folder.\n"
              "Open System Settings → Privacy & Security → Full Disk Access\n"
              "and enable it for Terminal, then run this again.")
        return 1
    except (WrongPasswordError, DeviceError) as exc:
        print(f"\n{exc}")
        return 1

    print(f"\nExported {result.message_count:,} messages across "
          f"{result.conversation_count} conversations to:\n  {result.out_dir}")
    for warning in result.warnings:
        print(f"  note: {warning}")
    return 0


def _list_devices() -> int:
    devices = list_devices()
    if not devices:
        print("No iPhone found. Plug one in with a cable, unlock it, and tap "
              "'Trust This Computer' if asked.")
        return 1
    for d in devices:
        print(f"{d.label}\n  {d.udid}")
    return 0


def _resolve_device(requested: str) -> str | None:
    """Turn a (possibly empty) --device value into a single UDID."""
    devices = list_devices()
    if not devices:
        print("No iPhone found. Plug one in with a cable, unlock it, and tap "
              "'Trust This Computer' if asked.")
        return None
    if requested:
        if any(d.udid == requested for d in devices):
            return requested
        print(f"No connected iPhone matches UDID {requested}. "
              f"Run --list-devices to see what's plugged in.")
        return None
    if len(devices) > 1:
        print("More than one iPhone is connected. Re-run with --device <UDID>:")
        for d in devices:
            print(f"  {d.udid}  ({d.label})")
        return None
    return devices[0].udid


if __name__ == "__main__":
    sys.exit(main())
