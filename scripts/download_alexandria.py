"""Alexandria Stage 2 — download the FULL congress-press corpus (2001 -> today) into the raw
mirror (gameplan §1.3). Download-only + memory-light: mirrors each month file to
data/raw/congress-press/ and discards records (the engine reads the mirror separately).

  python scripts/download_alexandria.py            # 2001-01 -> today
  python scripts/download_alexandria.py 2001-01    # explicit start
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import config, fetch, util  # noqa: E402

start = sys.argv[1] if len(sys.argv) > 1 else config.ALEXANDRIA_EPOCH
months = util.daterange_months(start, date.today().isoformat())
present = missing = total = 0
for (y, m) in months:
    recs = fetch.fetch_month(y, m)
    if recs is None:
        missing += 1
        continue
    present += 1
    total += len(recs)
    if present % 12 == 0 or len(recs) == 0:
        print(f"  {y}-{m:02d}: {len(recs):>5} releases  (cumulative {total:,})", flush=True)
print(f"\nAlexandria mirror complete: {present} months present, {missing} missing, {total:,} releases "
      f"in {fetch.MIRROR}", flush=True)
