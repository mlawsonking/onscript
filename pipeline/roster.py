"""Roster: bioguide -> {name, party, chamber, state}, derived from the corpus itself.

The press-release corpus carries member{bioguide_id, name, party, state, chamber} on every
record (R2), so the roster needs no external service (the unitedstates/congress-legislators
CSV export is unreliable from here). Built once from the raw mirror and cached; used for
first-sayer names and caucus sizes. Historical member-Congress party resolution (Alexandria
Stage 2, party switches) remains a v2 seam.

S74-11 (F7). The cache used to be write-once: `load` returned it whenever it existed and CI
restores it from the state asset, so a member first seen after it was built never got a name.
Three members seated since March rendered as "member name unavailable", and their own names in
their own releases were quarantined by the privacy scan, which resolves author names through
this map. `refresh` now merges, on every collect, the members the cache has not seen: from the
records just loaded from upstream, and from the committed date-effective roster. A merge never
drops an entry and never overwrites a present field with a blank. Chamber is corrected from the
term data (the date-effective roster's latest interval), because the corpus field carried
"house" for 77 sitting senators.
"""
from __future__ import annotations

from . import config, util

_CACHE = config.REFERENCE / "roster.json"
FIELDS = ("name", "party", "chamber", "state")


def _record_entry(rec: dict) -> tuple[str | None, dict]:
    m = rec.get("member") or {}
    bio = (m.get("bioguide_id") or m.get("bioguide") or "").strip()
    return (bio or None), {
        "name": (m.get("name") or "").strip() or None,
        "party": config.PARTY_NORMALIZE.get((m.get("party") or "").strip().lower()),
        "chamber": config.CHAMBER_NORMALIZE.get((m.get("chamber") or "").strip().lower()),
        "state": (m.get("state") or "").strip() or None,
    }


def build_from_mirror() -> dict[str, dict]:
    from . import fetch  # local import avoids any import cycle
    out: dict[str, dict] = {}
    for rec in fetch.load_mirror():
        bio, entry = _record_entry(rec)
        if not bio or bio in out:
            continue
        out[bio] = entry
    util.write_json(_CACHE, out)
    return out


def load(*, allow_build: bool = True) -> dict[str, dict]:
    cached = util.read_json(_CACHE, None)
    if cached is not None:
        return cached
    return build_from_mirror() if allow_build else {}


def _term_entries(roster_table: dict | None) -> dict[str, dict]:
    """{bioguide: fields} from the date-effective roster's latest interval per office."""
    if roster_table is None:
        from . import denominators
        roster_table = denominators.load_roster()
    out = {}
    for bio, row in (roster_table.get("offices") or {}).items():
        intervals = [iv for iv in (row.get("intervals") or []) if isinstance(iv, dict)]
        if not intervals:
            continue
        latest = max(intervals, key=lambda iv: iv.get("start") or "")
        chamber = (latest.get("chamber") or "").strip().lower() or None
        out[bio] = {
            "name": (row.get("name") or "").strip() or None,
            "party": config.PARTY_NORMALIZE.get((latest.get("party") or "").strip().lower()),
            "chamber": config.CHAMBER_NORMALIZE.get(chamber, chamber) if chamber else None,
            "state": (latest.get("state") or "").strip() or None,
            "_end": max((iv.get("end_exclusive") or "9999-12-31") for iv in intervals),
        }
    return out


def merge(cache: dict, records=(), *, roster_table: dict | None = None) -> tuple[dict, dict]:
    """Return (merged, stats). Pure: `cache` is not mutated.

    * an entry is never dropped;
    * a present field is never overwritten with a blank;
    * a blank field is filled from upstream records, then from the term data;
    * chamber is set from the term data whenever the term data has one (the corpus field is
      the unreliable one);
    * a member absent from the cache is added from the records first, then the term data.
    """
    merged = {bio: dict(entry) for bio, entry in (cache or {}).items() if isinstance(entry, dict)}
    stats = {"added": 0, "filled": 0, "chamber_corrected": 0, "before": len(merged)}
    seen_records = set()
    for rec in records or ():
        bio, entry = _record_entry(rec)
        if not bio or bio in seen_records:
            continue
        seen_records.add(bio)
        if bio not in merged:
            merged[bio] = entry
            stats["added"] += 1
            continue
        for key in FIELDS:
            if not merged[bio].get(key) and entry.get(key):
                merged[bio][key] = entry[key]
                stats["filled"] += 1
    for bio, entry in _term_entries(roster_table).items():
        if bio not in merged:
            # The term data names every office since 2001. Only offices serving on or after the
            # public epoch are imported, so the cache grows by the members who can author a
            # statement in the corpus and not by the 2001-2024 historical roster.
            if (entry.get("_end") or "") <= config.STAGE1_EPOCH:
                continue
            merged[bio] = {key: entry.get(key) for key in FIELDS}
            stats["added"] += 1
            continue
        for key in ("name", "party", "state"):
            if not merged[bio].get(key) and entry.get(key):
                merged[bio][key] = entry[key]
                stats["filled"] += 1
        if entry.get("chamber") and merged[bio].get("chamber") != entry["chamber"]:
            merged[bio]["chamber"] = entry["chamber"]
            stats["chamber_corrected"] += 1
    stats["after"] = len(merged)
    return merged, stats


def refresh(records=(), *, roster_table: dict | None = None) -> dict[str, dict]:
    """Load the cache (building it from the mirror if absent), merge what upstream and the term
    data know that it does not, persist it when anything changed, and return it. Called by every
    collect with the records it just loaded, so a member seated after the cache was built is
    named on the next run rather than never."""
    cached = util.read_json(_CACHE, None)
    if cached is None:
        cached = build_from_mirror()
    merged, stats = merge(cached, records, roster_table=roster_table)
    if merged != cached:
        util.write_json(_CACHE, merged)
    print(f"[roster] refresh: {stats}")
    return merged
