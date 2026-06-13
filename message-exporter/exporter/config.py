"""Project-wide constants."""
from __future__ import annotations

from pathlib import Path

# The phone number whose messages we are exporting (the owner of the iPhone).
OWNER_NUMBER = "+19258979008"

# Default country assumption when normalizing bare 10-digit numbers.
DEFAULT_REGION_PREFIX = "+1"

# Where exports land by default (kept outside the repo on purpose).
DEFAULT_OUTPUT_ROOT = Path.home() / "Documents" / "MessageExports"

# Where backups made *for* the user (via libimobiledevice) are kept between
# runs. Keeping them here is deliberate: idevicebackup2 backs up incrementally,
# so a retained backup turns every run after the first into a fast delta
# instead of another full overnight transfer.
DEFAULT_BACKUP_CACHE = DEFAULT_OUTPUT_ROOT / ".backup-cache"

# Backup file locations inside an iTunes/Finder backup.
SMS_DB_DOMAIN = "HomeDomain"
SMS_DB_RELATIVE_PATH = "Library/SMS/sms.db"
ADDRESSBOOK_DOMAIN = "HomeDomain"
ADDRESSBOOK_RELATIVE_PATH = "Library/AddressBook/AddressBook.sqlitedb"

# Standard macOS / Windows backup directories, in scan order.
MOBILESYNC_CANDIDATES = [
    Path.home() / "Library" / "Application Support" / "MobileSync" / "Backup",
    Path.home() / "AppData" / "Roaming" / "Apple Computer" / "MobileSync" / "Backup",
    Path.home() / "AppData" / "Roaming" / "Apple" / "MobileSync" / "Backup",
]
