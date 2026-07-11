"""Fast iteration helper: print top synchronized phrases for given days from the SAVED ledger
(data/state/ledger.json) without re-running the engine. Applies the display-time boilerplate
guard, so regex/knob tuning is testable in seconds.

  python scripts/query_ledger.py 2026-06-30 2026-07-09
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import build, config, util  # noqa: E402

led = util.read_json(config.STATE / "ledger.json", {})
print(f"ledger: {len(led)} phrases")
for day in sys.argv[1:] or ["2026-06-30"]:
    print(f"\n===== {day} — top synchronized (by peak) =====")
    for i, r in enumerate(build.top_synchronized(led, day, k=20), 1):
        fs = r["first_seen"]
        print(f"  {i:2d}. [{r['party']} {r['day_peak']:>3}u vel {r['velocity']:>4}] {r['ngram']!r}  (first {fs['date']} {fs['bioguide']})")
    print(f"----- {day} — top by velocity (spikes) -----")
    for i, r in enumerate(build.top_by_velocity(led, day, k=10), 1):
        print(f"  {i:2d}. [{r['party']} {r['day_peak']:>3}u vel {r['velocity']:>4}] {r['ngram']!r}")
