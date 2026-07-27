"""Pinned runtime environment disclosures for deterministic day boundaries."""
from __future__ import annotations

import hashlib
import locale
import sys
from pathlib import Path
from zoneinfo import TZPATH, ZoneInfo

from . import config


LOCALE = "C"
DAY_BOUNDARY = "prior America/New_York calendar day"


def _zone_path() -> Path | None:
    relative = Path(*config.TIMEZONE.split("/"))
    for root in TZPATH:
        candidate = Path(root) / relative
        if candidate.is_file():
            return candidate
    return None


def _tzdb_version() -> str | None:
    for root in TZPATH:
        candidate = Path(root) / "tzdata.zi"
        if candidate.is_file():
            first = candidate.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            if first.startswith("# version "):
                return first.removeprefix("# version ").strip()
    return None


def disclosure() -> dict:
    path = _zone_path()
    return {
        "python": ".".join(map(str, sys.version_info[:3])),
        "timezone": config.TIMEZONE,
        "tzdb_version": _tzdb_version(),
        "timezone_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path else None,
        "locale": LOCALE,
        "process_locale_observed": locale.setlocale(locale.LC_ALL, None),
        "day_boundary": DAY_BOUNDARY,
        "day_boundary_method": "product-day-v1",
    }


def zone() -> ZoneInfo:
    return ZoneInfo(config.TIMEZONE)
