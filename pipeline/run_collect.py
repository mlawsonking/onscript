"""RUN A "collect" (§2): pull+mirror congress-press -> normalize -> phrase engine -> ledger,
then submit/queue P1 extraction. Writes state (Release-asset-destined) + deterministic derived.

Dead-man semantics (§4 A1, §4 B9): stale upstream (>36h) -> proceed on mirror, degraded, ntfy;
daily volume < 40% of the trailing-14-day median -> ntfy. Skip-and-log throughout; never crash.
"""
from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import (config, deterministic, extract, fetch, llm, ops, roster,
                      runtime_environment, util)  # noqa: E402

STALE_HOURS = 36.0


def _volume_anomaly(statements, focus_day, *, maturity=None) -> dict:
    # Single definition in ops so collect and assemble compute the anomaly identically.
    return ops.volume_anomaly(statements, focus_day, maturity=maturity)


def collect(*, offline: bool, start: str, end: str, focus_day: str | None, do_extract: bool,
            reference_day: str | None = None) -> dict:
    freshness = {"ok": True, "note": "offline"} if offline else fetch.upstream_freshness()
    alerts = []
    degraded = False
    if not offline and freshness.get("ok"):
        if (freshness.get("age_hours") or 0) > STALE_HOURS:
            degraded = True
            alerts.append(f"upstream stale {freshness['age_hours']}h")
            ops.ntfy("OnScript collect", f"congress-press stale {freshness['age_hours']}h — running on mirror",
                     priority="high")

    # The restore ran in its own workflow step, so its cost arrives through the hand-off file
    # rather than a timer here. A first run (or a failed restore) simply has nothing to adopt.
    util.adopt_stage_timings()

    with util.stage_timer("mirror_pull"):
        if offline:
            records = fetch.load_mirror()
            pull = fetch.mirror_provenance()
        else:
            records, pull = fetch.pull_range(start, end)
            # merge with prior mirror months so the ledger stays a full-corpus function of raw
            records = fetch.load_mirror()
            alerts += ([] if pull["months_missing"] == 0 else [f"{pull['months_missing']} months missing"])

    roster.load()  # ensure the corpus-derived roster cache exists
    run_id = f"collect-{date.today().isoformat()}"
    res = deterministic.run(records, run_id=run_id, focus_day=focus_day, source_freshness=freshness)
    statements = res["statements"]
    focus_day = res["focus_day"]

    # RUN A meets the focus day while upstream is still delivering it, so the volume
    # comparison is gated on collection maturity. An immature day is logged, never paged: a
    # partial count is not a thin day. The upstream-stale alert above remains the dead-man for
    # a feed that has stopped. §S65.
    maturity = ops.collection_maturity(statements, focus_day,
                                       reference_day=reference_day or util.product_day())
    vol = _volume_anomaly(statements, focus_day, maturity=maturity)
    if vol["anomalously_low"]:
        alerts.append(f"volume {vol['today']} < 40% of median {vol['trailing_median']}")
        ops.ntfy("OnScript collect", f"low volume on {focus_day}: {vol['today']} (median {vol['trailing_median']})")
    elif not maturity["mature"]:
        alerts.append(f"volume comparison withheld on {focus_day}: {maturity['reason']} "
                      f"({vol['today']} so far, median {vol['trailing_median']})")

    extract_cost = {"skipped": True}
    if do_extract:
        sync = set(res["ledger"])
        _, extract_cost = extract.extract(statements, sync, util.read_json(config.TAXONOMY_FILE, {"topics": []})["topics"])
        if not llm.dry_run():  # pragma: no cover - real batch submission wired here when key present
            pass  # extraction batch already assembled by extract.extract in real mode

    manifest = dict(res["manifest"])
    manifest.update({"kind": "collect", "degraded": degraded, "volume": vol,
                     "extract": extract_cost, "alerts": alerts,
                     "upstream_provenance": pull,
                     "stage_timings_s": util.stage_timings(),
                     "runtime_environment": runtime_environment.disclosure()})
    util.write_json(config.DERIVED / "manifest" / f"{run_id}.json", manifest)
    util.write_json(config.DERIVED / "manifest" / "collect-latest.json", manifest)
    return {"manifest": manifest, "focus_day": focus_day, "res": res, "volume": vol, "degraded": degraded}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--start", default=config.STAGE1_EPOCH)
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--focus-day", default=None)
    ap.add_argument("--skip-extract", action="store_true")
    args = ap.parse_args()
    out = collect(offline=args.offline, start=args.start, end=args.end,
                  focus_day=args.focus_day, do_extract=not args.skip_extract)
    m = out["manifest"]
    print(f"===== RUN A collect — focus {out['focus_day']} (dry_run={llm.dry_run()}) =====")
    print(f"days present:  {m['days_present']}")
    print(f"normalize:     {m['normalize']}")
    print(f"phrase engine: {m['phrase_engine']}")
    print(f"volume:        {m['volume']}")
    print(f"degraded:      {m['degraded']}   alerts: {m['alerts']}")
    print(f"extract:       {m['extract']}")
    print(f"stage timings: {m['stage_timings_s']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
