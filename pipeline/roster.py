"""Roster join against unitedstates/congress-legislators (§1.2, R2).

The press-release corpus already carries reliable member{bioguide_id,party,state,chamber}
(R2), so the roster is *canonical validation + enrichment*, non-blocking (skip-and-log).
We use the CSV export so this stays stdlib-only (no PyYAML). Leadership roles are not in
the basic CSV -> leadership_role stays null in v1 (leadership-origin tagging is v3, §11.4).

Alexandria Stage 2 (§1.3) needs member-Congress-keyed party resolution via
legislators-historical (party switches). That is stubbed here with a clear seam; v1 only
covers the 119th, where the corpus party is reliable.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from . import config, util

_CSV_URL = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-current.csv"
_CACHE = config.REFERENCE / "legislators-current.csv"


def refresh_cache() -> bool:
    """Fetch the current roster CSV into the committed reference dir. Returns success."""
    try:
        data = util.http_get(_CSV_URL, timeout=60)
        _CACHE.write_bytes(data)
        return True
    except Exception:  # skip-and-log: roster is enrichment, never blocking
        return False


def load(*, allow_fetch: bool = True) -> dict[str, dict]:
    """bioguide -> {party, state, chamber, name}. Empty dict if unavailable."""
    if allow_fetch and not _CACHE.exists():
        refresh_cache()
    if not _CACHE.exists():
        return {}
    out: dict[str, dict] = {}
    text = _CACHE.read_text(encoding="utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        bio = (row.get("bioguide_id") or row.get("bioguide") or "").strip()
        if not bio:
            continue
        chamber = config.CHAMBER_NORMALIZE.get((row.get("type") or "").strip().lower(), None)
        party = config.PARTY_NORMALIZE.get((row.get("party") or "").strip().lower(), None)
        name = (row.get("last_name", "") + ", " + row.get("first_name", "")).strip(", ")
        out[bio] = {"party": party, "state": (row.get("state") or "").strip() or None,
                    "chamber": chamber, "name": name or None}
    return out
