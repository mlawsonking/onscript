"""P2: the clean-statement scan cache. Extends the redaction-cache pattern to the corpus walk.

THE COST. The W4 person-span gate runs a keyed hash over every token window of every statement,
on every run, for the whole corpus. The corpus is append-only: yesterday's statements were
scanned yesterday and were clean. Re-deriving that verdict every night is what took the daily
collect from ~60m to ~100m+ and through the 120m workflow ceiling on 2026-07-28/29.

WHAT IS CACHED, EXACTLY. One bit per statement text, and only in the affirmative: "no admitted
form occurs anywhere in this text". Nothing else. No offsets, no counts, no per-span structure,
no negative entries. A statement not known clean is scanned in full, every run.

WHY THAT BIT AND NOT A RICHER ONE. R-29.3 is absolute: no persisted or published artifact may
carry span offsets or any per-statement structure that lets a reader locate a suppressed name in
the public raw mirror. Span records are an attorney question riding the #105/#110 agenda, not an
engineering trade. So the cache stores the one verdict that cannot point at anything.

WHY THE KEYS ARE KEYED HASHES AND NOT sha256(text). data/state is tarred into a PUBLIC release
asset (see pipeline/privacy.py on why the salt lives outside data/reference). With plain digests
anyone holding the public mirror could hash each statement and test membership, and absence would
answer "which statements contained a suppressed name" for free. Under HMAC the membership test is
not computable without the salt, so the file answers no question at all to a reader who has it.
The cost is one hash per statement against three per token window, which is the whole point.

WHY INVALIDATION IS IN THE KEY, NOT A HEADER CHECK. The key commits to the method version, the
admitted-form fingerprint, and the entity-hierarchy version, so admitting a name or bumping either
version changes every key and no prior verdict can be served. A header check alone would still be
correct for a freshly loaded file, but it cannot protect a process whose gate is reloaded against
a different form list under the same salt: the in-memory set would answer from the old list. A
stale "clean" is a published name, so the guarantee belongs somewhere it cannot be skipped. The
header is validated too, so a file built under a different instrument is never even loaded.

FAIL-SAFE DIRECTION. Every failure mode resolves to "scan it again": an unreadable file, a
mismatched header, a malformed entry, a write error. There is no path on which a defect here
produces a "clean" answer that was not computed under the current instrument.

Stdlib only, and paths resolve lazily on purpose. pipeline/privacy.py imports this module, and
privacy is imported by read-only tools (the watchdog) that must not acquire pipeline.config's
import-time directory creation as a side effect (docs/37 rule 4, the S57 outage).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# PLAIN JSON, deliberately, like the redaction cache this extends. pipeline.redact must be able to
# parse every carrier it walks, and its JSON path opens files as text: a .json.gz cache made the
# Article XIII redaction step raise "unparseable JSON, cannot prove it is clean" and fail closed
# BEFORE the release upload, which is an authored outage (docs/37 rule 4). Compression would buy
# nothing anyway, since the file is tarred into a gzipped release asset. A permanent test asserts
# the carrier stays scannable.
CACHE_BASENAME = "clean-scan-cache.json"
SCHEMA_VERSION = 1
KIND = "clean-scan-cache"

# CACHE_VERSION, deliberately not METHOD_VERSION. It versions this file's key derivation and
# storage semantics so a change to either voids stored verdicts. It is NOT a measurement method
# version and must not enter instrument_fingerprint.METHOD_VERSION_PROVIDERS: the cache decides
# whether a verdict is recomputed, never what the verdict is, and the ledger is asserted
# byte-identical with it on and off. Putting it in the published fingerprint would announce an
# instrument change on a day the instrument did not move. The module's bytes are already covered
# by the fingerprint's measurement-tree hash, which is the right place for it.
CACHE_VERSION = "clean-scan-v1"

# 128 bits of a keyed hash. The birthday bound over a corpus of this size is ~1e-27, and the
# failure direction of a collision is a false "clean", so this is not a knob to trim.
KEY_HEX_CHARS = 32

_HEADER_FIELDS = ("schema_version", "kind", "cache_version", "forms_fingerprint",
                  "salt_fingerprint", "entity_hierarchy_version")

_ACTIVE = False
_PATH: Path | None = None
_HEADER: dict = {}
_CLEAN: set[str] = set()        # verdicts carried in from the last run, still valid
_OBSERVED: set[str] = set()     # verdicts this run stands behind; what flush() writes
_STATS: dict = {}


def _default_path() -> Path:
    from . import config  # lazy: see the module docstring on the import graph
    return Path(config.STATE) / CACHE_BASENAME


def _reset_stats() -> None:
    _STATS.clear()
    _STATS.update({"hits": 0, "misses": 0, "loaded": 0, "written": 0, "status": "inactive"})


_reset_stats()


def enabled() -> bool:
    """Operators can switch the cache off without a code change; the run then rescans everything."""
    return (os.environ.get("ONSCRIPT_SCAN_CACHE", "1") or "1").strip().lower() not in {
        "0", "false", "no", "off"}


def active() -> bool:
    return _ACTIVE


def stats() -> dict:
    return dict(_STATS)


def _read(path: Path, header: dict) -> tuple[set[str], str]:
    """Load the prior verdicts, or return an empty set and the reason it could not be used."""
    if not path.exists():
        return set(), "cold (no prior cache)"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except Exception as e:  # noqa: BLE001 - any unreadable cache means rescan, never trust
        return set(), f"unreadable, rescanning ({e.__class__.__name__})"
    if not isinstance(doc, dict):
        return set(), "malformed, rescanning"
    for field in _HEADER_FIELDS:
        if doc.get(field) != header.get(field):
            return set(), f"invalidated by {field}, full rescan"
    entries = doc.get("clean")
    if not isinstance(entries, list):
        return set(), "malformed entry list, rescanning"
    keys = {e for e in entries if isinstance(e, str) and len(e) == KEY_HEX_CHARS}
    if len(keys) != len(entries):
        # A truncated or hand-edited file is not a partially good file.
        return set(), "entries failed their shape check, full rescan"
    return keys, "loaded"


def activate(header: dict, *, path: Path | None = None) -> str:
    """Begin a cached run. Returns a short status string for the run log."""
    global _ACTIVE, _PATH, _HEADER, _CLEAN, _OBSERVED
    _reset_stats()
    _OBSERVED = set()
    _HEADER = dict(header)
    _PATH = Path(path) if path is not None else _default_path()
    if not enabled():
        _ACTIVE = False
        _CLEAN = set()
        _STATS["status"] = "disabled by ONSCRIPT_SCAN_CACHE"
        return _STATS["status"]
    _CLEAN, reason = _read(_PATH, _HEADER)
    _ACTIVE = True
    _STATS["loaded"] = len(_CLEAN)
    _STATS["status"] = reason
    return f"{reason}, {len(_CLEAN):,} prior clean verdict(s)"


def deactivate() -> None:
    global _ACTIVE, _CLEAN, _OBSERVED
    _ACTIVE = False
    _CLEAN = set()
    _OBSERVED = set()
    _STATS["status"] = "inactive"


def is_clean(key: str) -> bool:
    """Has this exact text already been proven to contain no admitted form, under this instrument?"""
    if not _ACTIVE:
        return False
    if key in _CLEAN:
        _STATS["hits"] += 1
        _OBSERVED.add(key)      # this run stands behind the verdict it served
        return True
    _STATS["misses"] += 1
    return False


def mark_clean(key: str) -> None:
    """Record a freshly computed clean verdict. Only ever called after a full scan found nothing."""
    if _ACTIVE:
        _OBSERVED.add(key)


def flush(*, path: Path | None = None) -> str:
    """Write exactly the verdicts this run stands behind.

    Replacement, not union: the file becomes what this run saw, so text that has left the corpus
    stops being carried forever. Every run walks the full corpus, so nothing durable is lost."""
    if not _ACTIVE:
        return "inactive, nothing written"
    target = Path(path) if path is not None else (_PATH or _default_path())
    doc = dict(_HEADER)
    doc["clean"] = sorted(_OBSERVED)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
        tmp.replace(target)
    except OSError as e:
        # A run that cannot persist its verdicts is a correct run that will rescan tomorrow.
        _STATS["status"] = f"write failed (non-fatal): {e}"
        return _STATS["status"]
    _STATS["written"] = len(_OBSERVED)
    return f"wrote {len(_OBSERVED):,} clean verdict(s) to {target.name}"
