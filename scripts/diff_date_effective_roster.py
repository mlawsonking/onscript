"""Diff two date-effective roster snapshots: per day, per party, eligible offices old and new.

Read before releasing a roster refresh (docs/07 P13). Prints both horizons, then every run of days
over which the D and R totals (voting and nonvoting offices, the population pages print since
S74-11) differ by the same offices, with the offices named, then every office whose intervals
changed anywhere. It computes; it does not judge. Read each named office against upstream's own term
dates.

    C:\\ProgramData\\miniconda3\\python.exe scripts/diff_date_effective_roster.py \\
        --old HEAD --new data/reference/date-effective-roster.json [--first 2025-01-03]

`--old` and `--new` are each a path or a git revision (read as <rev>:data/reference/...).
`--voting-only` compares voting members only, the population of audits written before 2026-11-21.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import config, denominators  # noqa: E402

REL = "data/reference/date-effective-roster.json"


def load(spec: str) -> dict:
    path = Path(spec)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{spec}:{REL}"]))


def _members(table: dict, day: str, party: str, voting_only: bool) -> set | None:
    offices = denominators.eligible_offices(day, party, roster_table=table, voting_only=voting_only)
    return None if offices is None else set(offices)


def day_runs(old: dict, new: dict, first: str, last: str, *, voting_only: bool = False) -> list[dict]:
    """Runs of consecutive days on which the same offices separate the two snapshots, per party.
    `totals` holds each party's (old, new) on the run's first day; a refused day is None."""
    runs: list[dict] = []
    day = date.fromisoformat(first)
    while day.isoformat() <= last:
        iso = day.isoformat()
        key, totals = {}, {}
        for party in config.COMPOSITE_PARTIES:
            before, after = _members(old, iso, party, voting_only), _members(new, iso, party, voting_only)
            totals[party] = (None if before is None else len(before), None if after is None else len(after))
            key[party] = (before is None, after is None,
                          tuple(sorted((after or set()) - (before or set()))),
                          tuple(sorted((before or set()) - (after or set()))))
        if runs and runs[-1]["key"] == key:
            runs[-1]["last"] = iso
        else:
            runs.append({"first": iso, "last": iso, "key": key, "totals": totals})
        day += timedelta(days=1)
    return runs


def office_changes(old: dict, new: dict) -> list[tuple[str, str, list, list]]:
    out = []
    for bioguide in sorted(set(old.get("offices", {})) | set(new.get("offices", {}))):
        a = (old["offices"].get(bioguide) or {}).get("intervals") or []
        b = (new["offices"].get(bioguide) or {}).get("intervals") or []
        sa = {json.dumps(x, sort_keys=True) for x in a}
        sb = {json.dumps(x, sort_keys=True) for x in b}
        if sa != sb:
            name = (new["offices"].get(bioguide) or old["offices"].get(bioguide))["name"]
            out.append((bioguide, name, sorted(sa - sb), sorted(sb - sa)))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--old", default="HEAD")
    parser.add_argument("--new", default=REL)
    parser.add_argument("--first", default=config.STAGE1_EPOCH)
    parser.add_argument("--voting-only", action="store_true")
    args = parser.parse_args(argv)
    old, new = load(args.old), load(args.new)
    h_old, h_new = denominators.roster_horizon(old), denominators.roster_horizon(new)
    print(f"horizon old {h_old} ({old['provenance']['revision'][:7]}), "
          f"new {h_new} ({new['provenance']['revision'][:7]})")
    last = max(h for h in (h_old, h_new) if h)
    names = {b: r["name"] for t in (old, new) for b, r in t["offices"].items()}
    for run in day_runs(old, new, args.first, last, voting_only=args.voting_only):
        days = (date.fromisoformat(run["last"]) - date.fromisoformat(run["first"])).days + 1
        bits = []
        for party, (_, _, added, removed) in run["key"].items():
            before, after = run["totals"][party]
            delta = "" if None in (before, after) else f" ({after - before:+d})"
            who = "".join(f" +{b} {names[b]}" for b in added) + "".join(f" -{b} {names[b]}" for b in removed)
            bits.append(f"{party} {before}->{after}{delta}{who}")
        print(f"{run['first']}..{run['last']} ({days}d)  " + "  ".join(bits))
    print("offices whose intervals changed:")
    for bioguide, name, removed, added in office_changes(old, new):
        print(f"  {bioguide} {name}")
        for row in removed:
            print(f"    - {row}")
        for row in added:
            print(f"    + {row}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
