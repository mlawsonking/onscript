"""Roster: bioguide -> {name, party, chamber, state}, derived from the corpus itself.

The press-release corpus carries member{bioguide_id, name, party, state, chamber} on every
record (R2), so the roster needs no external service (the unitedstates/congress-legislators
CSV export is unreliable from here). Built once from the raw mirror and cached; used for
first-sayer names and caucus sizes. Historical member-Congress party resolution (Alexandria
Stage 2, party switches) remains a v2 seam.
"""
from __future__ import annotations

from . import config, util

_CACHE = config.REFERENCE / "roster.json"


def build_from_mirror() -> dict[str, dict]:
    from . import fetch  # local import avoids any import cycle
    out: dict[str, dict] = {}
    for rec in fetch.load_mirror():
        m = rec.get("member") or {}
        bio = (m.get("bioguide_id") or m.get("bioguide") or "").strip()
        if not bio or bio in out:
            continue
        out[bio] = {
            "name": (m.get("name") or "").strip() or None,
            "party": config.PARTY_NORMALIZE.get((m.get("party") or "").strip().lower()),
            "chamber": config.CHAMBER_NORMALIZE.get((m.get("chamber") or "").strip().lower()),
            "state": (m.get("state") or "").strip() or None,
        }
    util.write_json(_CACHE, out)
    return out


def load(*, allow_build: bool = True) -> dict[str, dict]:
    cached = util.read_json(_CACHE, None)
    if cached is not None:
        return cached
    return build_from_mirror() if allow_build else {}
