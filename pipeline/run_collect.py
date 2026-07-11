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

from pipeline import config, deterministic, extract, fetch, llm, ops, roster, util  # noqa: E402

STALE_HOURS = 36.0


def _volume_anomaly(statements, focus_day) -> dict:
    by_day = Counter(s["published_at"] for s in statements if s.get("lane") == 1)
    days = sorted(by_day)
    prior = [by_day[d] for d in days if d < focus_day][-14:]
    today = by_day.get(focus_day, 0)
    med = statistics.median(prior) if prior else 0
    low = bool(med) and today < 0.4 * med
    return {"today": today, "trailing_median": med, "anomalously_low": low}


def collect(*, offline: bool, start: str, end: str, focus_day: str | None, do_extract: bool) -> dict:
    freshness = {"ok": True, "note": "offline"} if offline else fetch.upstream_freshness()
    alerts = []
    degraded = False
    if not offline and freshness.get("ok"):
        if (freshness.get("age_hours") or 0) > STALE_HOURS:
            degraded = True
            alerts.append(f"upstream stale {freshness['age_hours']}h")
            ops.ntfy("OnScript collect", f"congress-press stale {freshness['age_hours']}h — running on mirror",
                     priority="high")

    if offline:
        records = fetch.load_mirror()
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

    vol = _volume_anomaly(statements, focus_day)
    if vol["anomalously_low"]:
        alerts.append(f"volume {vol['today']} < 40% of median {vol['trailing_median']}")
        ops.ntfy("OnScript collect", f"low volume on {focus_day}: {vol['today']} (median {vol['trailing_median']})")

    extract_cost = {"skipped": True}
    if do_extract:
        sync = set(res["ledger"])
        _, extract_cost = extract.extract(statements, sync, util.read_json(config.TAXONOMY_FILE, {"topics": []})["topics"])
        if not llm.dry_run():  # pragma: no cover - real batch submission wired here when key present
            pass  # extraction batch already assembled by extract.extract in real mode

    manifest = dict(res["manifest"])
    manifest.update({"kind": "collect", "degraded": degraded, "volume": vol,
                     "extract": extract_cost, "alerts": alerts})
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
