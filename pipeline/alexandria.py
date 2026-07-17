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
from .search import provenance

ALEX = config.STATE / "alexandria"           # per-Congress shard outputs (on X: via junction)
LANES_DIR = ALEX / "lanes"                    # per-LANE shards (docs/18) — a subdirectory ON PURPOSE:
# `merge()` globs ALEX.glob("ledger-*.json"), and a flat `ledger-113.propublica.json` WOULD match it
# (verified) — merge would double-count and its manifest's int(stem.split("-")[1]) would choke on
# "113.propublica". A non-recursive glob never descends into `lanes/`, so the combined shards and
# merge() stay literally untouched (docs/18 §1, Art. VI schema promise).
FIRST_CONGRESS = 107                          # 2001-01-03
LAST_CONGRESS = 119                           # through 2026
# Per-lane shards exist ONLY for the symmetric span (docs/17 §1). 107-112 stay combined-only: their
# pre-2013 tails are 99.9% single-party (legacy) / ~100% R (scraper), so a per-lane shard there would
# be an invitation to a poisoned statistic (docs/18 §2). A per-lane loader for them RAISES.
PER_LANE_CONGRESSES = range(113, 120)
LANES = ("propublica", "scraped")


def congress_range(n: int) -> tuple[str, str]:
    """[start, end) ISO dates for the Nth Congress (seated ~Jan 3 of the odd year)."""
    seat_year = 2001 + 2 * (n - 107)
    return f"{seat_year}-01-03", f"{seat_year + 2}-01-03"


def lane_shard_path(kind: str, n: int, lane: str | None):
    """Path for a shard file. `lane=None` -> the combined shard in ALEX/ (today's behaviour, unchanged).
    A lane -> ALEX/lanes/{kind}-{n}.{lane}.json. Raises for 107-112 (combined-only) or an unknown lane
    — the guard that stops a poisoned pre-2013 per-lane statistic from ever being built or read."""
    if lane is None:
        return ALEX / f"{kind}-{n}.json"
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r} — expected one of {LANES}")
    if n not in PER_LANE_CONGRESSES:
        raise provenance.LaneIsolationError(
            f"congress {n} has no per-lane shard: per-lane shards exist only for {PER_LANE_CONGRESSES.start}"
            f"-{PER_LANE_CONGRESSES.stop - 1} (docs/18 §2). The pre-2013 tails are 99.9% single-party, so a "
            f"per-lane shard there would be a poisoned statistic. Use the combined shard (lane=None).")
    return LANES_DIR / f"{kind}-{n}.{lane}.json"


def load_congress_records(n: int, lane: str | None = None) -> list[dict]:
    """Load ONLY the Nth Congress's records from the mirror (memory-light — one era at a time).

    `lane` in {'propublica','scraped'} filters records by `provenance.instrument_of` (docs/18 §2) —
    the lane is a property of the RECORD, applied BEFORE normalize, so normalize and PhraseEngine stay
    untouched. `load_congress_records` is the third and last place `date_source` used to die (the
    Session-16 finding); with `lane` it becomes lane-aware at the source. A record whose instrument is
    unknown (untagged) matches no lane and is excluded — but the 19 real untagged records have null
    dates and never pass the date window anyway."""
    if lane is not None and n not in PER_LANE_CONGRESSES:
        raise provenance.LaneIsolationError(
            f"congress {n} is combined-only (docs/18 §2) — no per-lane record load for {n}")
    start, end = congress_range(n)
    recs: list[dict] = []
    for (y, m) in util.daterange_months(start, end):
        f = fetch.MIRROR / f"{y}-{m:02d}.jsonl"
        if not f.exists():
            continue
        for r in util.iter_jsonl(f):
            d = (r.get("date") or "")[:10]
            if not (start <= d < end):
                continue
            if lane is not None and provenance.instrument_of(r) != lane:
                continue
            recs.append(r)
    return recs


def run_shard(n: int, lane: str | None = None) -> dict | None:
    """Build the ledger/discipline/coverage/summary shards for one Congress.

    `lane=None` writes the combined shards to ALEX/ exactly as before (byte-identical — the daily
    site/Archive substrate, docs/18 §3.4). A lane writes per-lane shards to ALEX/lanes/. The lane is
    filtered at the record level before normalize; everything downstream is identical, so a per-lane
    shard is schema-identical to a combined one and the Search readers need no special case beyond the
    path."""
    out_dir = ALEX if lane is None else LANES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    # `_lane` is spliced in ONLY for a per-lane run, so the combined shard-{n}.json stays byte-identical
    # to the pre-change output (docs/18 §3.4) — the daily site/Archive substrate must not shift.
    _lane = {"lane": lane} if lane is not None else {}
    recs = load_congress_records(n, lane=lane)
    if not recs:
        util.write_json(lane_shard_path("shard", n, lane), {"congress": n, **_lane, "records": 0, "empty": True})
        return {"congress": n, **_lane, "records": 0, "statements": 0, "ledger": 0}
    statements = normalize.normalize_records(recs, run_id=f"alex-{n}" + (f"-{lane}" if lane else ""))
    engine = PhraseEngine()
    ledger = engine.build(statements, progress=len(statements) > 100_000)
    util.write_json(lane_shard_path("ledger", n, lane), ledger, indent=None)
    util.write_json(lane_shard_path("discipline", n, lane), engine.discipline_index())
    util.write_json(lane_shard_path("coverage", n, lane), build.coverage_tables(statements))
    summary = {"congress": n, **_lane, "range": list(congress_range(n)), "records": len(recs),
               "statements": len(statements), "ledger": len(ledger),
               "norm": getattr(normalize.normalize_records, "last_stats", {})}
    util.write_json(lane_shard_path("shard", n, lane), summary)
    return summary


def reconcile_lane_shards(n: int) -> dict:
    """Acceptance reconciliation for one Congress (docs/18 §3.1-§3.2). Verifies the RAW record
    partition is EXACT and measures the post-normalize statement-count delta, attributing it to
    cross-lane exact-id duplicates (a url+text that appears under both instruments is deduped once in
    the combined run but kept once per lane). Writes the numbers into each lane's shard summary and
    returns the reconciliation. A statements delta beyond ±0.5% is a stop-and-diagnose (docs/18 §3.2)."""
    combined = util.read_json(lane_shard_path("shard", n, None), {}) or {}
    pro = util.read_json(lane_shard_path("shard", n, "propublica"), {}) or {}
    scr = util.read_json(lane_shard_path("shard", n, "scraped"), {}) or {}

    rec_c, rec_p, rec_s = combined.get("records", 0), pro.get("records", 0), scr.get("records", 0)
    st_c, st_p, st_s = combined.get("statements", 0), pro.get("statements", 0), scr.get("statements", 0)

    # attribute the statement delta: statement_id is sha of url+text, so a value present in BOTH lanes
    # is deduped in combined but kept once per lane -> +1 to the per-lane sum. Cheap one-pass recompute
    # (no PhraseEngine): just the id sets.
    def id_set(lane):
        ids = set()
        for r in load_congress_records(n, lane=lane):
            url = (r.get("url") or "").strip()
            text = r.get("text") or ""
            if url and text.strip():
                ids.add(util.statement_id(url, text))
        return ids
    ids_p, ids_s = id_set("propublica"), id_set("scraped")
    cross_lane_id_dups = len(ids_p & ids_s)

    st_delta = (st_p + st_s) - st_c
    st_pct = (st_delta / st_c) if st_c else 0.0
    recon = {
        "congress": n,
        "records": {"combined": rec_c, "propublica": rec_p, "scraped": rec_s,
                    "sum_lanes": rec_p + rec_s, "delta": (rec_p + rec_s) - rec_c,
                    "exact_partition": (rec_p + rec_s) == rec_c},
        "statements": {"combined": st_c, "propublica": st_p, "scraped": st_s,
                       "sum_lanes": st_p + st_s, "delta": st_delta,
                       "pct": round(st_pct, 5), "within_0.5pct": abs(st_pct) <= 0.005},
        "attribution": {"cross_lane_exact_id_dups": cross_lane_id_dups,
                        "explains_delta": cross_lane_id_dups == st_delta},
    }
    # record the numbers where §3.2 asks: in each lane's shard summary
    for lane, summ in (("propublica", pro), ("scraped", scr)):
        if summ:
            summ["reconciliation"] = recon
            util.write_json(lane_shard_path("shard", n, lane), summ)
    return recon


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
    return {"manifest": manifest, "ledger_entries": len(merged), "coverage": coverage, "ledger": merged}
