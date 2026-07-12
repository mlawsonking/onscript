"""Alexandria Stage 2 (§1.3): the 25-year ledger, built by SHARDING per Congress and merging.

Why sharded: the full 2001-2026 corpus (~690k statements) in one two-pass process commits
~25-30 GB and can blow the system commit limit. Each Congress (~50-200k statements) processes
in a fresh ~1-5 GB process — safe, resumable, and exactly the "matrix of jobs, ~2 Congresses
per job" the gameplan specs. Per-Congress document-frequency weighting falls out for free
(§1.3): each shard's DF is that era's DF. The merge combines the per-Congress ledgers into one.

Determinism note: shards write to X: via the state junction; the merge is a pure function of
the shard ledgers.
"""
from __future__ import annotations

from collections import defaultdict

from . import build, config, fetch, normalize, util
from .phrases import PhraseEngine

ALEX = config.STATE / "alexandria"           # per-Congress shard outputs (on X: via junction)
FIRST_CONGRESS = 107                          # 2001-01-03
LAST_CONGRESS = 119                           # through 2026


def congress_range(n: int) -> tuple[str, str]:
    """[start, end) ISO dates for the Nth Congress (seated ~Jan 3 of the odd year)."""
    seat_year = 2001 + 2 * (n - 107)
    return f"{seat_year}-01-03", f"{seat_year + 2}-01-03"


def load_congress_records(n: int) -> list[dict]:
    """Load ONLY the Nth Congress's records from the mirror (memory-light — one era at a time)."""
    start, end = congress_range(n)
    recs: list[dict] = []
    for (y, m) in util.daterange_months(start, end):
        f = fetch.MIRROR / f"{y}-{m:02d}.jsonl"
        if not f.exists():
            continue
        for r in util.iter_jsonl(f):
            d = (r.get("date") or "")[:10]
            if start <= d < end:
                recs.append(r)
    return recs


def run_shard(n: int) -> dict | None:
    ALEX.mkdir(parents=True, exist_ok=True)
    recs = load_congress_records(n)
    if not recs:
        util.write_json(ALEX / f"shard-{n}.json", {"congress": n, "records": 0, "empty": True})
        return {"congress": n, "records": 0, "statements": 0, "ledger": 0}
    statements = normalize.normalize_records(recs, run_id=f"alex-{n}")
    engine = PhraseEngine()
    ledger = engine.build(statements, progress=len(statements) > 100_000)
    util.write_json(ALEX / f"ledger-{n}.json", ledger, indent=None)
    util.write_json(ALEX / f"discipline-{n}.json", engine.discipline_index())
    util.write_json(ALEX / f"coverage-{n}.json", build.coverage_tables(statements))
    summary = {"congress": n, "range": list(congress_range(n)), "records": len(recs),
               "statements": len(statements), "ledger": len(ledger),
               "norm": getattr(normalize.normalize_records, "last_stats", {})}
    util.write_json(ALEX / f"shard-{n}.json", summary)
    return summary


def merge(focus_day: str | None = None) -> dict:
    """Merge all per-Congress shard ledgers -> the full 25-year ledger + derived JSON."""
    merged: dict[str, dict] = {}
    for f in sorted(ALEX.glob("ledger-*.json")):
        for ng, e in (util.read_json(f, {}) or {}).items():
            m = merged.get(ng)
            if m is None:
                merged[ng] = e
                continue
            m["daily"].update(e["daily"])  # Congresses span disjoint date ranges -> disjoint days
            fe, fm = e["first_seen"], m["first_seen"]
            if fe.get("date") and (not fm.get("date") or fe["date"] < fm["date"]):
                m["first_seen"] = fe
            m["peak_units"] = max(m.get("peak_units", 0), e.get("peak_units", 0))
            m["df_weight"] = min(m.get("df_weight", 1.0), e.get("df_weight", 1.0))

    discipline: dict[str, dict] = defaultdict(dict)
    for f in sorted(ALEX.glob("discipline-*.json")):
        for party, days in (util.read_json(f, {}) or {}).items():
            discipline[party].update(days)

    coverage: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    for f in sorted(ALEX.glob("coverage-*.json")):
        for year, parties in (util.read_json(f, {}) or {}).items():
            for p, c in parties.items():
                coverage[year][p] += c
    coverage = {y: dict(p) for y, p in sorted(coverage.items())}

    util.write_json(config.STATE / "ledger.json", merged, indent=None)

    days_present = sorted({d for e in merged.values() for d in e["daily"]})
    focus_day = focus_day or (days_present[-1] if days_present else util.product_day())
    summary = build.build_derived([], merged, dict(discipline), config.DERIVED,
                                  focus_day=focus_day, coverage=coverage)
    manifest = {
        "schema_version": 1, "kind": "alexandria-merge", "generated_at": util.now_utc_iso(),
        "congresses": [int(f.stem.split("-")[1]) for f in sorted(ALEX.glob("ledger-*.json"))],
        "ledger_entries": len(merged), "focus_day": focus_day,
        "coverage_years": sorted(coverage.keys()),
        "epoch": [days_present[0], days_present[-1]] if days_present else None,
    }
    util.write_json(config.DERIVED / "manifest" / "alexandria.json", manifest)
    return {"manifest": manifest, "ledger_entries": len(merged), "coverage": coverage}
