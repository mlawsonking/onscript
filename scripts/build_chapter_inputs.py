"""Build chapter inputs from the ALREADY-MERGED ledger (skip re-merge). Writes chapter_inputs.json
+ the finalize-done sentinel the generator waits on. Used when the merge is done but the (now
optimized) input build needs to (re)run.

  python scripts/build_chapter_inputs.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import chapters, config, util  # noqa: E402

t = time.time()
print(f"[inputs] loading merged ledger (X:) …", flush=True)
ledger = util.read_json(config.STATE / "ledger.json", {})
coverage = util.read_json(config.DERIVED / "coverage.json", {})
print(f"[inputs] ledger {len(ledger):,} phrases loaded in {time.time()-t:.0f}s; building era + monthly …", flush=True)

era = chapters.build_era_inputs(ledger, coverage)
print(f"[inputs] era done ({len(era)}) at {time.time()-t:.0f}s; monthly …", flush=True)
monthly = chapters.build_monthly_inputs(ledger)
inputs = era + monthly
chapters.write_inputs(inputs)
sufficient = sum(1 for i in inputs if i["sufficient"])
print(f"[inputs] {len(era)} era + {len(monthly)} monthly = {len(inputs)} total, {sufficient} sufficient "
      f"(in {time.time()-t:.0f}s)", flush=True)

util.write_json(config.DERIVED / "manifest" / "finalize-done.json",
                {"generated_at": util.now_utc_iso(), "ledger_entries": len(ledger),
                 "chapter_inputs": len(inputs), "sufficient": sufficient, "coverage": coverage})
print("[inputs] sentinel written — generator will proceed.", flush=True)
