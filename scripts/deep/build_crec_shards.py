"""D1.c/d — per-Congress CREC ledger shards + published coverage audits (docs/15 §3).

  $ python scripts/deep/build_crec_shards.py --congresses 113,114,115,116

For each congress: verify every year is COMPLETELY crawled, assert genre isolation on the loaded set,
build the ledger/discipline/coverage shards on X:, write the committed audit JSON, and run the D1
acceptance smoke query (top Extensions phrases by party, `crec_boilerplate.suppress()` applied).

Three things this refuses to do, each of which would produce an artifact that lies:

* **Build a congress with a half-crawled year.** A truncated year is indistinguishable from a quiet
  one once it is inside a shard — it just looks like less speech. Completeness is verified against the
  published GovInfo sitemap (days-done in the crawl manifest vs days the sitemap lists), not guessed
  from file size. `--allow-partial` exists for deliberate exceptions and stamps the audit JSON with
  `"partial": true` so the artifact carries its own caveat.
* **Suppress boilerplate into the shard.** Congresses 107-110 were built raw, `suppress()` being a
  display/analysis-time filter by design (docs/15 §9 D4-pre). Applying it at build time here would
  fork the instrument mid-lane and quietly invalidate every within-lane cross-era comparison — the
  exact "genre confound in a trend costume" failure, wearing the costume of a fix. The shard stays raw;
  the smoke query shows the suppressor doing its job on top of it.
* **Trust that the loaded rows are one lane.** `lanes.lane_of()` is called explicitly before the build,
  so a stray press row in the crec state dir raises instead of silently entering a deep shard.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.deep import crec, crec_boilerplate, lanes  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
AUDIT_DIR = REPO / "data" / "derived" / "crec" / "audit"


def settled_days(state: Path) -> tuple[dict[int, set[str]], dict[int, set[str]]]:
    """(crawled, upstream_gaps) per year — the two ways a sitemap-listed day can be SETTLED.

    A day is settled-unavailable when GovInfo's own metadata endpoint has no MODS for a package its
    sitemap lists (served as HTTP 200 + an HTML error page — see `crec.looks_like_mods`). Those days
    can never be crawled, so counting them as "pending" would make 100% unreachable and the word
    "complete" meaningless. They are accounted for and DISCLOSED instead."""
    crawled: dict[int, set[str]] = defaultdict(set)
    gaps: dict[int, set[str]] = defaultdict(set)
    man = state / "crawl-manifest.jsonl"
    if man.exists():
        with open(man, encoding="utf-8") as f:
            for line in f:
                for marker, sink in (('"day-done:CREC-', crawled), ('"day-nomods:CREC-', gaps)):
                    if marker not in line:
                        continue
                    try:
                        uid = json.loads(line)["id"]
                    except Exception:
                        continue               # torn line from a hard-killed crawl
                    pkg = uid.split(":", 1)[1]
                    sink[int(pkg[len("CREC-"):][:4])].add(pkg)
    # On-disk evidence of the same fact, from before the marker existed: a mirrored ".mods.xml" whose
    # bytes are not MODS. Reading it here means a build need not wait for a heal pass to be honest.
    for p in (lanes.lane_raw("crec") / "mods").glob("*/CREC-*.mods.xml"):
        try:
            if not crec.looks_like_mods(p.read_bytes()[:512]):
                gaps[int(p.name[len("CREC-"):][:4])].add(p.name[:-len(".mods.xml")])
        except OSError:
            continue
    return dict(crawled), dict(gaps)


def completeness(year: int, done: set[str], gaps: set[str], *, offline: bool) -> dict:
    """days settled (crawled + upstream-unavailable) vs the year's published sitemap. The sitemap is the
    only external truth about how many Record days exist; without it we can only report, never certify."""
    base = {"year": year, "days_done": len(done), "upstream_gaps": sorted(gaps)}
    if offline:
        return {**base, "sitemap_days": None, "missing": None, "complete": None, "checked": "offline"}
    try:
        listed = set(crec.enumerate_days(year))
    except Exception as e:                     # skip-and-log: a sitemap outage must not corrupt a build
        return {**base, "sitemap_days": None, "missing": None, "complete": None,
                "checked": f"sitemap FAILED: {e}"}
    missing = sorted(listed - done - gaps)
    return {**base, "sitemap_days": len(listed), "missing": len(missing), "missing_sample": missing[:10],
            "complete": not missing, "checked": "sitemap"}


def smoke_top_phrases(ledger: dict, party: str, k: int = 8) -> list[dict]:
    """Top coordinated Extensions phrases for one party — peak single-day co-users — with CREC
    procedural/bill-title furniture suppressed. This is the D1 acceptance query."""
    rows = []
    for ng, e in ledger.items():
        peak = max((d.get(party, 0) for d in e["daily"].values()), default=0)
        if peak >= 3:
            rows.append({"ng": ng, "peak": peak, "n": e["n"]})
    rows = crec_boilerplate.suppress(rows)
    rows.sort(key=lambda r: (-r["peak"], -r["n"], r["ng"]))
    return rows[:k]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--congresses", required=True, help="comma-separated, e.g. 113,114,115,116")
    ap.add_argument("--allow-partial", action="store_true", help="build even if a year is incomplete")
    ap.add_argument("--offline", action="store_true", help="skip the sitemap completeness check")
    ap.add_argument("--dry-run", action="store_true", help="check completeness only; build nothing")
    args = ap.parse_args()

    state = lanes.lane_state("crec")
    done, gaps = settled_days(state)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    rc = 0

    for c in (int(x) for x in args.congresses.split(",")):
        years = crec.congress_years(c)
        print(f"\n=== congress {c} ({years[0]}-{years[1]}) " + "=" * 40)
        checks = [completeness(y, done.get(y, set()), gaps.get(y, set()), offline=args.offline)
                  for y in years]
        for ck in checks:
            print(f"  {ck['year']}: {ck['days_done']} days crawled / {ck['sitemap_days']} in sitemap "
                  f"-> {'COMPLETE' if ck['complete'] else 'INCOMPLETE' if ck['complete'] is False else 'UNVERIFIED'}"
                  + (f"  (missing {ck['missing']}, e.g. {ck['missing_sample'][:3]})" if ck.get("missing") else "")
                  + (f"  [{len(ck['upstream_gaps'])} upstream gap: {ck['upstream_gaps']}]"
                     if ck["upstream_gaps"] else ""))
        partial = any(ck["complete"] is False for ck in checks)
        if partial and not args.allow_partial:
            print(f"  REFUSING to build congress {c}: a truncated year is indistinguishable from a quiet "
                  f"one inside a shard. Finish the crawl, or pass --allow-partial to stamp it.")
            rc = 1
            continue
        if args.dry_run:
            continue

        statements = crec._load_statements(years)
        if not statements:
            print(f"  REFUSING: no statements on disk for {years}")
            rc = 1
            continue
        lane = lanes.lane_of(statements)                  # genre isolation, Law 1, enforced in code
        if lane != "crec":
            raise lanes.GenreIsolationError(f"expected lane 'crec', resolved {lane!r}")
        print(f"  {len(statements):,} statements · lane={lane} · building shard…")

        res = crec.build_congress_shard(c, progress=False)
        print(f"  shard: {res['ledger_entries']:,} ledger entries from {res['statements']:,} statements")

        audit = crec.audit_congress(c)
        audit["congress"] = c
        if partial:
            audit["partial"] = True
            audit["partial_note"] = "built from an INCOMPLETE crawl; year coverage below is truncated"
        audit["crawl_completeness"] = checks
        (AUDIT_DIR / f"congress-{c}.json").write_text(json.dumps(audit, indent=1), encoding="utf-8")
        for w, r in audit["windows"].items():
            print(f"  audit {w}: D={r['members']['D']}/{r['statements']['D']} "
                  f"R={r['members']['R']}/{r['statements']['R']} ratio={r['symmetry_ratio']} "
                  f"-> {'PASS' if r['PASS'] else 'FAIL'}")
        if len(audit["windows_passing"]) != len(audit["windows"]):
            print(f"  ⚠ NOT every window passes: {audit['windows_passing']}")
            rc = 1

        ledger = json.loads((state / f"ledger-{c}.json").read_text(encoding="utf-8"))
        for party in ("D", "R"):
            top = smoke_top_phrases(ledger, party)
            print(f"  top {party} Extensions phrases (boilerplate-suppressed):")
            for r in top[:5]:
                print(f"     {r['peak']:>3} co-users · {r['ng']}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
