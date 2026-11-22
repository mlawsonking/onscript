"""Build data/reference/date-effective-roster.json from unitedstates/congress-legislators at a PINNED revision.

Deterministic: the same revision and the same two source files produce the same bytes. The revision is
an argument, never "the latest", because a roster refresh changes published denominators going forward
and is a release decision (S74-11 Package 1c). The builder never decides that; it only makes the snapshot
reproducible and states the horizon it can speak for.

Usage (fetch the two files at the revision, verify their sha256, write the snapshot):

    C:\\ProgramData\\miniconda3\\python.exe scripts/build_date_effective_roster.py \\
        --revision 4458244308621d0570a15008f46888b7a87645eb --retrieved-at 2026-07-27T00:00:00Z \\
        --out <path>

`--source-dir DIR` reads legislators-current.yaml and legislators-historical.yaml from DIR instead of
fetching them (the files must still be the ones at the revision; their hashes are recorded either way).
`--no-valid-through` omits the provenance `valid_through` field, which is how the 2026-07-27 snapshot was
written; without it the reader derives the horizon from the intervals (pipeline/denominators.py).

Schema (unchanged from X8): offices[bioguide] = {name, intervals: [{chamber, district, end_exclusive,
official_url, party, start, state, voting_status}]}, intervals in source term order, one interval per
term (a term carrying party_affiliations is split at each affiliation's start, so a party switch is
effective on its recorded date). Terms whose end is on or after 2001-01-01 are kept.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

FILES = ("legislators-current.yaml", "legislators-historical.yaml")
RAW_URL = "https://raw.githubusercontent.com/unitedstates/congress-legislators/{rev}/{name}"
SOURCE = "unitedstates/congress-legislators"
SOURCE_URL = "https://github.com/unitedstates/congress-legislators"
WINDOW_START = "2001-01-01"
# Delegates and the resident commissioner sit in the House without a floor vote.
NONVOTING_JURISDICTIONS = frozenset({"AS", "DC", "GU", "MP", "PR", "VI"})
CHAMBERS = {"rep": "House", "sen": "Senate"}
TRANSFORMATION = ("terms from 2001 onward; chamber normalized; voting status derived from delegate "
                  "jurisdictions")


def _fetch(revision: str, name: str) -> bytes:
    with urllib.request.urlopen(RAW_URL.format(rev=revision, name=name), timeout=120) as resp:
        return resp.read()


def _yaml_load(data: bytes):
    import yaml
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    return yaml.load(data, Loader=loader)


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _name(person: dict) -> str:
    name = person.get("name") or {}
    if name.get("official_full"):
        return name["official_full"]
    return " ".join(part for part in (name.get("first"), name.get("middle"), name.get("last")) if part)


def _intervals(term: dict, *, split_affiliations: bool) -> list[dict]:
    chamber = CHAMBERS.get(term.get("type"))
    start, end = _iso(term.get("start")), _iso(term.get("end"))
    base = {
        "chamber": chamber,
        "district": term.get("district") if chamber == "House" else None,
        "official_url": term.get("url"),
        "state": term.get("state"),
        "voting_status": ("nonvoting" if chamber == "House" and term.get("state") in NONVOTING_JURISDICTIONS
                          else "voting"),
    }
    affiliations = ([row for row in (term.get("party_affiliations") or []) if isinstance(row, dict)]
                    if split_affiliations else [])
    if not affiliations:
        return [{**base, "end_exclusive": end, "party": term.get("party"), "start": start}]
    return [{**base, "end_exclusive": seg_end, "party": party, "start": seg_start}
            for seg_start, seg_end, party in _affiliation_segments(term, affiliations)]


def _affiliation_segments(term: dict, affiliations: list[dict]) -> list[tuple[str, str, str]]:
    """Partition one term at each affiliation's recorded start: (start, end_exclusive, party).

    S74-13. A party switch is effective on the date its new affiliation starts. Upstream writes an
    affiliation's `end` in two conventions: equal to the next start (Jeffords 2001, Specter 2009,
    Manchin 2024) or the day before it, an inclusive last day (Van Drew 2019, Amash 2019 and 2020,
    Mitchell 2020, Sinema 2022, Kiley 2026). Copying `end` into an exclusive bound, as the first
    version of this flag did, seated the office nowhere on that last day. So every segment ends where
    the next one starts, and the last ends with the term. Any other shape (a start outside the term,
    starts out of order, an end that fits neither convention) stops the build: it is reported, not
    worked around."""
    term_start, term_end = _iso(term.get("start")), _iso(term.get("end"))
    rows = [(_iso(row.get("start")), _iso(row.get("end")), row.get("party")) for row in affiliations]
    who = f"{term.get('type')} {term.get('state')} {term_start}..{term_end}"
    if rows[0][0] != term_start or rows[-1][1] != term_end:
        raise ValueError(f"party_affiliations do not span the term ({who}): {rows}")
    starts = [row[0] for row in rows]
    if any(not value for value in starts) or starts != sorted(set(starts)):
        raise ValueError(f"party_affiliations starts are missing or out of order ({who}): {rows}")
    out = []
    for index, (row_start, row_end, party) in enumerate(rows):
        seg_end = rows[index + 1][0] if index + 1 < len(rows) else term_end
        if index + 1 < len(rows):
            inclusive = (date.fromisoformat(seg_end) - timedelta(days=1)).isoformat()
            if row_end not in (seg_end, inclusive):
                raise ValueError(f"party_affiliations end {row_end} fits neither convention before the "
                                 f"next start {seg_end} ({who}): {rows}")
        out.append((row_start, seg_end, party))
    return out


def build(sources: dict[str, bytes], *, revision: str, retrieved_at: str,
          valid_through: str | None, split_affiliations: bool = False) -> dict:
    offices: dict[str, dict] = {}
    for name in FILES:
        for person in _yaml_load(sources[name]) or []:
            bioguide = (person.get("id") or {}).get("bioguide")
            if not bioguide:
                continue
            intervals = []
            for term in person.get("terms") or []:
                if CHAMBERS.get(term.get("type")) is None:
                    continue
                if (_iso(term.get("end")) or "9999-12-31") < WINDOW_START:
                    continue
                intervals.extend(_intervals(term, split_affiliations=split_affiliations))
            if intervals:
                offices[bioguide] = {"intervals": intervals, "name": _name(person)}
    provenance = {
        "files": [{"path": name, "sha256": hashlib.sha256(sources[name]).hexdigest(),
                   "url": RAW_URL.format(rev=revision, name=name)} for name in FILES],
        "license": "CC0-1.0",
        "retrieved_at": retrieved_at,
        "revision": revision,
        "source": SOURCE,
        "source_url": SOURCE_URL,
        "transformation": TRANSFORMATION,
    }
    if valid_through:
        provenance["valid_through"] = valid_through
    return {
        "interval_semantics": "start inclusive, end exclusive",
        "kind": "date-effective-congressional-roster",
        "offices": dict(sorted(offices.items())),
        "provenance": provenance,
        "schema_version": 1,
        "vacancy_semantics": "an office is absent between the prior interval end and successor interval start",
        "voting_status_semantics": "delegates and the resident commissioner are nonvoting",
    }


def default_valid_through(table: dict, retrieved_at: str) -> str | None:
    """The last day the snapshot can speak for: the day before the scheduled end shared by the House
    intervals open on the retrieval date. Same rule as denominators.roster_horizon."""
    day = retrieved_at[:10]
    ends = Counter()
    for row in table["offices"].values():
        for interval in row["intervals"]:
            if (interval.get("chamber") == "House" and (interval.get("start") or "") <= day
                    < (interval.get("end_exclusive") or "9999-12-31")):
                ends[interval["end_exclusive"]] += 1
    if not ends:
        return None
    end = sorted(ends.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return (date.fromisoformat(end) - timedelta(days=1)).isoformat()


def serialize(table: dict) -> bytes:
    return (json.dumps(table, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--revision", required=True, help="full 40-character congress-legislators commit")
    parser.add_argument("--retrieved-at", required=True, help="ISO timestamp recorded in provenance")
    parser.add_argument("--source-dir", type=Path, help="read the two YAML files here instead of fetching")
    parser.add_argument("--valid-through", help="explicit horizon (YYYY-MM-DD); default derived")
    parser.add_argument("--no-valid-through", action="store_true", help="omit valid_through (pre-S74-11 shape)")
    parser.add_argument("--split-party-affiliations", action="store_true",
                        help="split a term at each party_affiliations start (the committed shape from S74-13)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if len(args.revision) != 40 or any(c not in "0123456789abcdef" for c in args.revision):
        parser.error("--revision must be a full lowercase 40-character commit hash (pinned, never a branch)")
    sources = {}
    for name in FILES:
        sources[name] = ((args.source_dir / name).read_bytes() if args.source_dir
                         else _fetch(args.revision, name))
    table = build(sources, revision=args.revision, retrieved_at=args.retrieved_at, valid_through=None,
                  split_affiliations=args.split_party_affiliations)
    if not args.no_valid_through:
        valid_through = args.valid_through or default_valid_through(table, args.retrieved_at)
        if valid_through:
            table["provenance"]["valid_through"] = valid_through
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(serialize(table))
    print(f"[roster] {len(table['offices'])} offices, "
          f"{sum(len(r['intervals']) for r in table['offices'].values())} intervals, revision "
          f"{args.revision[:7]}, valid_through {table['provenance'].get('valid_through')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
