"""Merge all per-Congress Alexandria shard ledgers into the full 25-year ledger + derived JSON.

  python scripts/alexandria_merge.py            # focus = latest day present
  python scripts/alexandria_merge.py 2026-06-30
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import alexandria  # noqa: E402

focus = sys.argv[1] if len(sys.argv) > 1 else None
res = alexandria.merge(focus_day=focus)
m = res["manifest"]
print("===== ALEXANDRIA MERGE =====")
print(f"congresses merged: {m['congresses']}")
print(f"epoch:             {m['epoch']}")
print(f"ledger entries:    {m['ledger_entries']:,}")
print(f"coverage years:    {m['coverage_years'][0]}..{m['coverage_years'][-1]} ({len(m['coverage_years'])} yrs)")
print("\nper-year x per-party coverage (the temporal-honesty layer, §1.3):")
for y, parties in sorted(res["coverage"].items()):
    print(f"  {y}: D={parties.get('D',0):>6}  R={parties.get('R',0):>6}  I={parties.get('I',0):>4}")
