"""A1 — pull the congress-press corpus and mirror it immutably (§4 A1, D3).

Mirroring every pull into our own store is the resilience decision (§0/D3): the entire
symmetric two-party corpus rests on one volunteer repo, so we never depend on it being up
at run time — we depend on our mirror. Staleness of the upstream fires the dead-man switch.
"""
from __future__ import annotations

import json
import hashlib

from . import config, util

MIRROR = config.RAW / "congress-press"


def upstream_freshness() -> dict:
    """Return {ok, pushed_at, age_hours} for the congress-press repo (dead-man input)."""
    try:
        data = json.loads(util.http_get(config.CONGRESS_PRESS_API, timeout=30))
        pushed = data.get("pushed_at")  # e.g. 2026-07-10T09:23:45Z
        from datetime import datetime, timezone
        dt = datetime.strptime(pushed, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
        return {"ok": True, "pushed_at": pushed, "age_hours": round(age_h, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e), "pushed_at": None, "age_hours": None}


def source_revision() -> str:
    """Resolve the upstream default branch to one exact commit."""
    repo = json.loads(util.http_get(config.CONGRESS_PRESS_API, timeout=30))
    branch = repo.get("default_branch") or "main"
    commit = json.loads(util.http_get(f"{config.CONGRESS_PRESS_API}/commits/{branch}", timeout=30))
    revision = commit.get("sha")
    if not isinstance(revision, str) or len(revision) != 40:
        raise ValueError("upstream did not return an exact commit")
    return revision


def _fetch_month(year: int, month: int,
                 revision: str | None = None) -> tuple[list[dict] | None, dict | None]:
    url = config.CONGRESS_PRESS_MONTH_URL.format(year=year, month=month)
    if revision:
        url = url.replace("/main/", f"/{revision}/")
    try:
        raw, headers = util.http_get_metadata(url, timeout=90)
    except Exception:
        return None, None
    records = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    # Mirror immutably (append-only; overwrite the month snapshot each pull).
    MIRROR.mkdir(parents=True, exist_ok=True)
    util.write_jsonl(MIRROR / f"{year}-{month:02d}.jsonl", records, gzipped=False)
    return records, {
        "path": f"data/{year}/{year}-{month:02d}.jsonl",
        "url": url,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "etag": headers.get("etag"),
        "collected_at": util.now_utc_iso(),
        "records": len(records),
    }


def fetch_month(year: int, month: int) -> list[dict] | None:
    """Return parsed records for one month while preserving the legacy call contract."""
    records, _provenance = _fetch_month(year, month)
    return records


def pull_range(start: str, end: str) -> tuple[list[dict], dict]:
    """Pull every month file in [start, end] (YYYY-MM-DD). Returns (records, stats)."""
    records: list[dict] = []
    months_present = 0
    months_missing = 0
    revision = source_revision()
    files = []
    for (y, m) in util.daterange_months(start, end):
        recs, provenance = _fetch_month(y, m, revision)
        if recs is None:
            months_missing += 1
            continue
        months_present += 1
        records.extend(recs)
        files.append(provenance)
    stats = {"months_present": months_present, "months_missing": months_missing,
             "records": len(records), "range": [start, end],
             "upstream_commit": revision, "files": files,
             "collected_at": util.now_utc_iso()}
    return records, stats


def load_mirror() -> list[dict]:
    """Read all mirrored month files (degraded-mode source when upstream is down, §4 A1)."""
    out: list[dict] = []
    if MIRROR.exists():
        for f in sorted(MIRROR.glob("*.jsonl")):
            out.extend(util.iter_jsonl(f))
    return out


def mirror_provenance() -> dict:
    """Describe the exact local mirror used by an offline collection."""
    files = []
    for path in sorted(MIRROR.glob("*.jsonl")):
        files.append({
            "path": path.as_posix(),
            "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "etag": None,
            "collected_at": None,
        })
    return {"mode": "offline-mirror", "upstream_commit": None, "files": files,
            "collected_at": util.now_utc_iso()}
