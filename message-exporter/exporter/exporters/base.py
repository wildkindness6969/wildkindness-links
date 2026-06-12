"""Exporter contract. Future Converse AI roster/JSONL exporters implement
this same interface and consume the same ExportBundle."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from ..models import ExportBundle

ProgressFn = Callable[[str, float], None]


class Exporter(ABC):
    name: str = "exporter"

    @abstractmethod
    def export(self, bundle: ExportBundle, out_dir: Path,
               progress: ProgressFn | None = None) -> list[Path]:
        """Write output files for `bundle` into `out_dir`; return their paths."""


def safe_filename(name: str, max_len: int = 60) -> str:
    cleaned = "".join(c if c.isalnum() or c in " ._-()" else "_" for c in name).strip()
    cleaned = " ".join(cleaned.split())
    return (cleaned or "conversation")[:max_len]
