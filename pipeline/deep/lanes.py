"""Deep Archive lane registry + plumbing (docs/15 §D0.2). Stdlib-only.

Every deep-lane unit is tagged with its `source` and carries REQUIRED provenance (url + unit_date +
stable_id) or it does not enter the ledger. The press spine is the untagged default. GENRE ISOLATION
(Law 1) is enforced here: `lane_of()` raises on any row set that mixes sources, so a series can never
silently compare CREC floor speech to press releases.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .. import config

# The onscript-data root (X:), followed through the state junction so it is machine-portable and never
# hardcodes a drive letter. Overridable for tests/other machines.
DEEP_ROOT = Path(os.environ.get("ONSCRIPT_DEEP_ROOT", "") or os.path.realpath(config.STATE)).parent

# Lane registry. `press` is the spine (untagged; window = ledger-availability, not raw symmetry).
LANES: dict[str, dict] = {
    "press":            {"genre": "press_release",        "window": "2013-2026",  "role": "spine"},
    "crec":             {"genre": "congressional_record", "window": "2001-2026",  "role": "deep"},
    "dcinbox":          {"genre": "e_newsletter",         "window": "2010-2012",  "role": "crosscheck"},
    "academic_archive": {"genre": "press_release",        "window": "2005-2012",  "role": "crosscheck"},
    "loc_webarchive":   {"genre": "press_release",        "window": "2003-2012",  "role": "conditional"},
    "wayback":          {"genre": "press_release",        "window": "per-member", "role": "adhoc"},
}
DEEP_LANES = [k for k in LANES if k != "press"]


def lane_raw(source: str) -> Path:
    return DEEP_ROOT / source / "raw"


def lane_state(source: str) -> Path:
    return DEEP_ROOT / source / "state"


# --- the deep-statement tag: source + REQUIRED provenance (Law: 100% provenance) -----------------
class ProvenanceError(ValueError):
    pass


def tag(stmt: dict, source: str, *, url: str, unit_date: str, stable_id: str, **extra) -> dict:
    """Stamp a statement with its lane source + required provenance. Raises if the lane is unknown or
    any provenance field is missing — a unit without full provenance never enters the ledger."""
    if source not in LANES:
        raise ValueError(f"unknown lane {source!r}")
    if not (url and unit_date and stable_id):
        raise ProvenanceError("provenance incomplete: url + unit_date + stable_id are all required")
    return {**stmt, "source": source, "url": url, "unit_date": unit_date, "stable_id": stable_id, **extra}


# --- GENRE ISOLATION (Law 1, enforced in code) ---------------------------------------------------
class GenreIsolationError(RuntimeError):
    pass


def source_of(row: dict) -> str:
    """A row's lane. The press spine is untagged -> 'press'."""
    return row.get("source") or "press"


def lane_of(rows) -> str | None:
    """The single source shared by every row, or raise. This is the in-code guard that forbids a
    cross-lane series (e.g. crec-2008 next to press-2015 — a genre confound in a trend costume)."""
    sources = {source_of(r) for r in rows}
    if len(sources) > 1:
        raise GenreIsolationError(f"cross-lane series forbidden — mixes {sorted(sources)}; "
                                  "cross-era comparisons are permitted within ONE lane only (docs/15 Law 1)")
    return next(iter(sources)) if sources else None


# --- resumable, polite crawl manifest (Law: mirror-first, resumable) -----------------------------
POLITE = {"min_interval_s": 0.34, "user_agent": "onscript-research/1.0 (+https://onscript.news)"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class CrawlManifest:
    """Append-only JSONL checkpoint of fetched units (stable_id + sha256 + bytes) so a killed crawl
    resumes cleanly and every mirrored artifact is hash-verifiable. §D0.2/D0.3."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._seen: dict[str, str] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue   # a torn final line from a hard-killed crawl -> skip; the crawl resumes clean
                self._seen[r["id"]] = r.get("sha")

    def seen(self, uid: str) -> bool:
        return uid in self._seen

    def record(self, uid: str, sha: str, nbytes: int = 0, meta: dict | None = None) -> None:
        self._seen[uid] = sha
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            row = {"id": uid, "sha": sha, "bytes": nbytes}
            if meta:
                row["meta"] = meta
            f.write(json.dumps(row, separators=(",", ":")) + "\n")

    def __len__(self) -> int:
        return len(self._seen)
