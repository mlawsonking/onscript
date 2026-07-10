"""Stage-1 backfill (gameplan §1.3): pull congress-press from the 119th-Congress epoch
(2025-01-03) to today, run the deterministic engine ($0 LLM), and prove the moat.

Usage (from repo root):
  python scripts/backfill_stage1.py                 # full 2025-epoch -> today
  python scripts/backfill_stage1.py --start 2026-06-01   # smaller slice for a fast check
  python scripts/backfill_stage1.py --offline        # rebuild from the existing raw mirror
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

try:  # Windows dev consoles default to cp1252; the runner is utf-8. Force utf-8 either way.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, deterministic, fetch  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=config.STAGE1_EPOCH)
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--offline", action="store_true", help="rebuild from raw mirror, no network")
    ap.add_argument("--focus-day", default=None)
    args = ap.parse_args()

    run_id = f"backfill-stage1-{date.today().isoformat()}"

    if args.offline:
        print(f"[offline] loading raw mirror from {fetch.MIRROR} …")
        records = fetch.load_mirror()
        freshness = {"ok": True, "note": "offline rebuild from mirror"}
    else:
        freshness = fetch.upstream_freshness()
        print(f"[freshness] congress-press pushed_at={freshness.get('pushed_at')} "
              f"age_hours={freshness.get('age_hours')}")
        print(f"[pull] {args.start} → {args.end} (mirroring raw to {fetch.MIRROR}) …")
        records, pull_stats = fetch.pull_range(args.start, args.end)
        print(f"[pull] months present={pull_stats['months_present']} "
              f"missing={pull_stats['months_missing']} records={pull_stats['records']}")

    print(f"[engine] normalizing + building ledger over {len(records)} records …")
    res = deterministic.run(records, run_id=run_id, focus_day=args.focus_day, source_freshness=freshness)

    m = res["manifest"]
    print("\n===== STAGE 1 PROOF =====")
    print(f"days present:        {m['days_present']}")
    print(f"normalize:           {m['normalize']}")
    print(f"phrase engine:       {m['phrase_engine']}")
    for p in config.ALL_PARTIES:
        print(f"  party {p}:           {m['per_party'][p]}")
    print(f"derived:             {m['derived']}")
    print(f"\nfocus day:           {res['focus_day']}")

    # Boilerplate proof (§1.4.5): top-20 synchronized phrases on the focus day.
    from pipeline import build
    top = build.top_synchronized(res["ledger"], res["focus_day"], k=20)
    print(f"\nTop synchronized phrases on {res['focus_day']} (boilerplate proof — should be political, not template):")
    for i, r in enumerate(top, 1):
        fs = r["first_seen"]
        print(f"  {i:2d}. [{r['party']} {r['day_peak']:>3} units] {r['ngram']!r}  "
              f"(first: {fs['date']} {fs['bioguide']})")
    if not top:
        print("  (no synchronized phrases on the focus day — pick a busier --focus-day)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
