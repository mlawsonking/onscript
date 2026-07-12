"""Auto-finalize: wait for all Alexandria shards -> merge -> build chapter inputs.

Runs in the background after the shard driver. When it completes, the 25-year ledger + coverage
tables + chapter_inputs.json exist, and the agentic chapter workflow can commence.

  python scripts/alexandria_finalize.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import alexandria, chapters, config, util  # noqa: E402

CONGRESSES = list(range(alexandria.FIRST_CONGRESS, alexandria.LAST_CONGRESS + 1))
MAX_WAIT_S = 6 * 60 * 60  # give up after 6h (well beyond the ~3h shard run) and merge what exists

# 1. wait for every shard to have written its summary (or MAX_WAIT, then proceed)
waited = 0
while True:
    done = [n for n in CONGRESSES if (alexandria.ALEX / f"shard-{n}.json").exists()]
    if len(done) == len(CONGRESSES) or waited >= MAX_WAIT_S:
        break
    print(f"[finalize] waiting for shards: {len(done)}/{len(CONGRESSES)} done "
          f"(missing {[n for n in CONGRESSES if n not in done]})", flush=True)
    time.sleep(20)
    waited += 20

print(f"[finalize] {len(done)}/{len(CONGRESSES)} shards present — merging …", flush=True)
res = alexandria.merge()
m = res["manifest"]
print(f"[finalize] merged: {m['ledger_entries']:,} ledger phrases, epoch {m['epoch']}", flush=True)

# 2. build the grounded chapter inputs — era essays + monthly chapters (the full tranche),
#    both coverage-gated (thin ones get honest code stubs, never fabricated prose).
era = chapters.build_era_inputs(res["ledger"], res["coverage"])
monthly = chapters.build_monthly_inputs(res["ledger"])
inputs = era + monthly
chapters.write_inputs(inputs)
sufficient = sum(1 for i in inputs if i["sufficient"])
print(f"[finalize] chapter inputs: {len(era)} era + {len(monthly)} monthly = {len(inputs)} total; "
      f"{sufficient} with adequate coverage (rest -> code stubs)", flush=True)

# 3. sentinel + coverage snapshot for quick review
util.write_json(config.DERIVED / "manifest" / "finalize-done.json",
                {"generated_at": util.now_utc_iso(), "ledger_entries": m["ledger_entries"],
                 "epoch": m["epoch"], "chapter_inputs": len(inputs), "sufficient": sufficient,
                 "coverage": res["coverage"]})
print("[finalize] DONE — ledger + coverage + chapter_inputs.json ready.", flush=True)
