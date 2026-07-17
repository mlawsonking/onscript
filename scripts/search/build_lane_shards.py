"""Build the per-lane alexandria shards for 113-119 (docs/18 §2), resumable, then reconcile each.

Order front-loads the SCRAPED lane (117-119, ~175k statements, 117 already built) so its hypotheses
can run before the heavier PROPUBLICA lane (113-116, ~495k statements) finishes. Skips a (congress,
lane) whose shard summary already exists unless --force. Reconciliation (§3.1/§3.2) runs per congress
once BOTH its lanes exist. PYTHONHASHSEED is pinned (set by the launcher) so the ledger's key order —
which is otherwise per-process randomized via _doc_ngrams' set iteration — is reproducible; the
analysis is order-invariant regardless (the Search readers stream all entries).

Re-runnable:  PYTHONHASHSEED=0 python scripts/search/build_lane_shards.py
              PYTHONHASHSEED=0 python scripts/search/build_lane_shards.py --force 115
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import alexandria as A

# BOTH lanes for every congress 113-119 (docs/18 §2), so the per-congress reconcile covers all seven.
# The analysis only ever reads propublica@113-116 and scraped@117-119; the OTHER-lane shards exist for
# the §3.1/§3.2 acceptance and the brief's "supplementary check" (the 2013-2020 scraped tail, never
# pooled). propublica@118-119 are 0-record (the lane dies 2021-01-03) — their emptiness IS the seam on
# record. Analysis-heavy pairs first (scraped 117-119, propublica 113-116), then the small remainder.
PLAN = ([(c, "scraped") for c in (117, 118, 119)] +
        [(c, "propublica") for c in (113, 114, 115, 116)] +
        [(c, "scraped") for c in (113, 114, 115, 116)] +      # 2013-2020 scraped tail (small; supplementary)
        [(c, "propublica") for c in (117, 118, 119)])         # 117 tiny stub; 118/119 empty


def main():
    force = "--force" in sys.argv
    only = [int(a) for a in sys.argv[1:] if a.isdigit()] or None
    t0 = time.time()
    for c, lane in PLAN:
        if only and c not in only:
            continue
        summ = A.lane_shard_path("shard", c, lane)
        if summ.exists() and not force:
            print(f"[skip] {lane} congress {c} (shard summary exists)", flush=True)
            continue
        t = time.time()
        print(f"[build] {lane} congress {c} …", flush=True)
        res = A.run_shard(c, lane=lane)
        print(f"[build] {lane} congress {c}: records={res.get('records')} statements={res.get('statements')} "
              f"ledger={res.get('ledger')} ({time.time()-t:.0f}s)", flush=True)

    # reconcile every congress whose BOTH lane shards now exist
    print("\n[reconcile] per-congress acceptance (§3.1/§3.2)", flush=True)
    for c in range(113, 120):
        if A.lane_shard_path("shard", c, "propublica").exists() and A.lane_shard_path("shard", c, "scraped").exists():
            r = A.reconcile_lane_shards(c)
            rec, st = r["records"], r["statements"]
            flag = "" if (rec["exact_partition"] and st["within_0.5pct"]) else "  <<< STOP-AND-DIAGNOSE"
            print(f"  c{c}: records {rec['propublica']}+{rec['scraped']}={rec['sum_lanes']} vs {rec['combined']} "
                  f"(exact={rec['exact_partition']}); statements delta={st['delta']} ({st['pct']*100:.3f}%, "
                  f"ok={st['within_0.5pct']}); cross_lane_id_dups={r['attribution']['cross_lane_exact_id_dups']}{flag}", flush=True)
    print(f"\n[done] {time.time()-t0:.0f}s total", flush=True)


if __name__ == "__main__":
    main()
