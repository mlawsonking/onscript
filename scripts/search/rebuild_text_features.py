"""Rebuild text_features.jsonl with the L1 lane fields (`ds`/`inst`) present.

The on-disk cache dated 2026-07-16 01:58 predates the Session-16 L1 fix, so its rows carry no
provenance and every S2 hypothesis reading it via `iter_text_features` is lane-blind BY SUBSTRATE
(docs/17 §3). `harness.build_text_features` already emits the fields; only the cache is stale.

Re-runnable: python scripts/search/rebuild_text_features.py
"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline.search import harness

t0 = time.time()
print("rebuilding text_features.jsonl (congresses 113-119) ...", flush=True)
stats = harness.build_text_features(congresses=range(113, 120), progress=True)
print(f"DONE {stats} in {time.time()-t0:.0f}s", flush=True)

# Prove the lane fields landed, and report the lane mix — the whole point of the rebuild.
from collections import Counter
mix = Counter()
n = 0
for r in harness.iter_text_features():
    n += 1
    mix[(r.get("ds"), r.get("inst"))] += 1
print("rows:", n)
print("lane mix:", json.dumps({f"{k[0]}/{k[1]}": v for k, v in mix.most_common()}, indent=2))
