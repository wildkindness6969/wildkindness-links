"""Uniform access to backup files, plain or encrypted.

Both readers copy the requested file into a private temp workdir and hand
back that copy — downstream code never opens databases inside the backup
itself, and `close()` shreds the workdir so no decrypted message data is
left behind.
"""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from ..config import (
    ADDRESSBOOK_DOMAIN,
    ADDRESSBOOK_RELATIVE_PATH,
    SMS_DB_DOMAIN,
    SMS_DB_RELATIVE_PATH,
)
from . import manifest


class WrongPasswordError(Exception):
    pass


class BackupReader:
    def __init__(self) -> None:
        self.workdir = Path(tempfile.mkdtemp(prefix="message-exporter-"))

    def get_file(self, domain: str, relative_path: str) -> Path | None:
        raise NotImplementedError

    def get_sms_db(self) -> Path | None:
        return self.get_file(SMS_DB_DOMAIN, SMS_DB_RELATIVE_PATH)

    def get_addressbook_db(self) -> Path | None:
        try:
            return self.get_file(ADDRESSBOOK_DOMAIN, ADDRESSBOOK_RELATIVE_PATH)
        except Exception:
            return None   # contacts are optional; numbers still export fine

    def close(self) -> None:
        shutil.rmtree(self.workdir, ignore_errors=True)

    def __enter__(self) -> "BackupReader":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class PlainBackupReader(BackupReader):
    def __init__(self, backup_dir: Path) -> None:
        super().__init__()
        self.backup_dir = Path(backup_dir)

    def get_file(self, domain: str, relative_path: str) -> Path | None:
        src = manifest.resolve_file(self.backup_dir, domain, relative_path)
        if src is None:
            return None
        dest = self.workdir / Path(relative_path).name
        shutil.copy2(src, dest)
        # SQLite sidecar files must travel with the database for WAL replay.
        for suffix in ("-wal", "-shm"):
            sidecar = manifest.resolve_file(self.backup_dir, domain,
                                            relative_path + suffix)
            if sidecar is not None:
                shutil.copy2(sidecar, self.workdir / (dest.name + suffix))
        return dest


class EncryptedBackupReader(BackupReader):
    def __init__(self, backup_dir: Path, password: str) -> None:
        super().__init__()
        try:
            from iphone_backup_decrypt import EncryptedBackup
        except ImportError as exc:
            raise RuntimeError(
                "The 'iphone-backup-decrypt' package is required for encrypted "
                "backups. Run: pip install iphone-backup-decrypt"
            ) from exc
        self._backup = EncryptedBackup(backup_directory=str(backup_dir),
                                       passphrase=password)

    def test_password(self) -> None:
        """Force keybag decryption now so a wrong password fails fast."""
        try:
            self._backup.test_decryption()
        except Exception as exc:
            raise WrongPasswordError(
                "That password didn't unlock the backup."
            ) from exc

    def get_file(self, domain: str, relative_path: str) -> Path | None:
        dest = self.workdir / Path(relative_path).name
        try:
            self._backup.extract_file(relative_path=relative_path,
                                      domain_like=domain,
                                      output_filename=str(dest))
        except TypeError:
            # Older iphone-backup-decrypt versions have no domain_like kwarg.
            self._backup.extract_file(relative_path=relative_path,
                                      output_filename=str(dest))
        except FileNotFoundError:
            return None
        except Exception as exc:
            if "password" in str(exc).lower() or "passphrase" in str(exc).lower():
                raise WrongPasswordError(str(exc)) from exc
            raise
        return dest if dest.exists() else None


def open_backup(backup_dir: Path, password: str | None = None) -> BackupReader:
    """Pick the right reader for this backup, validating the password up front."""
    from .locate import read_backup_info

    info = read_backup_info(backup_dir)
    encrypted = info.encrypted if info else False
    if encrypted:
        if not password:
            raise WrongPasswordError("This backup is encrypted — a password is required.")
        reader = EncryptedBackupReader(backup_dir, password)
        reader.test_password()
        return reader
    return PlainBackupReader(backup_dir)


def open_sms_copy_check(path: Path) -> None:
    """Sanity-check that an extracted file is really a chat database."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    if "message" not in tables:
        raise RuntimeError("The extracted sms.db does not look like a chat database.")
