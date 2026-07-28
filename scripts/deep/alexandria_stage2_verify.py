"""E3 dry prep: verify the Alexandria Stage 2 EMBEDDING inputs against the current shard inventory.

Alexandria Stage 2's DETERMINISTIC pass is already complete (docs/04 Session 3: the 25-year ledger,
curves, discipline index, coverage tables, and era/monthly chapters). What is NOT built is the OPTIONAL
4080 layer (docs/03 §1.4): local GPU sentence embeddings (all-MiniLM-L6-v2) over the whole corpus, plus
a local 8-14B model topic-tag pass, feeding Archive exhibits (de-facto caucuses, 25-year topic ownership,
frame-war maps). Those are Archive EXHIBITS, dark until released, one-time, on Michael's box, disclosed.

This script VERIFIES the inputs that pass will consume, against the shard inventory the deterministic
pass built, so the GPU run starts from a known-consistent corpus. It is the runbook's precondition gate:

  press mirror (Lane-1 congress-press) records, per Congress  ==  alexandria shard `records`
  the embeddable unit count                                   ==  alexandria shard `statements` (normalized)
  CREC E-lane (the deep instrument) E-statements present       for 107-119

$0, CPU-only, deterministic, READ-ONLY. It NEVER starts the GPU job; that is Michael's machine time and
his call (the charter: nothing recurring on a personal machine; one-time backfill is capex, disclosed).

  python scripts/deep/alexandria_stage2_verify.py
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import alexandria as A, util  # noqa: E402
from pipeline.search import harness as H  # noqa: E402
from pipeline.deep import lanes  # noqa: E402

CONGRESSES = range(107, 120)


def _congress_of(date: str):
    try:
        y = int(date[:4]); m = int(date[5:7]); d = int(date[8:10])
    except Exception:
        return None
    n = 107 + (y - 2001) // 2
    if (y - 2001) % 2 == 0 and (m, d) < (1, 3):
        n -= 1
    return n


def press_pass():
    """One streaming pass over the press mirror (no text read: records + lane only)."""
    rec_by_c = Counter()
    lane_by_c = defaultdict(Counter)
    for r in H.iter_statements(congresses=None, with_text=False):
        c = r["congress"]
        rec_by_c[c] += 1
        lane_by_c[c][r.get("date_source") or "untagged"] += 1
    return rec_by_c, lane_by_c


def crec_pass():
    """Count CREC Extensions statements per Congress from crec/state/E/statements-{year}.jsonl."""
    state = lanes.lane_state("crec")
    e_dir = state / "E"
    stmt_by_c = Counter()
    years = []
    if e_dir.exists():
        for f in sorted(e_dir.glob("statements-*.jsonl")):
            years.append(f.stem.split("-")[1])
            for row in util.iter_jsonl(f):
                # CREC rows carry an authoritative `congress`; fall back to the unit/published date.
                c = row.get("congress") or _congress_of((row.get("unit_date") or row.get("published_at") or "")[:10])
                if c is not None:
                    stmt_by_c[int(c)] += 1
    ledgers = {n: (state / f"ledger-{n}.json").exists() for n in CONGRESSES}
    return stmt_by_c, years, ledgers


def main():
    print("== Alexandria Stage 2 embedding-input verification (E3 dry prep) ==\n")
    rec_by_c, lane_by_c = press_pass()

    print("PRESS MIRROR (Lane-1) vs alexandria shard inventory:")
    print("  cong | mirror recs | shard recs | delta | shard statements (embeddable units)")
    ok = True
    tot_mirror = tot_shard_r = tot_stmt = 0
    lane_totals = Counter()
    for n in CONGRESSES:
        s = util.read_json(A.lane_shard_path("shard", n, None), {}) or {}
        sr = s.get("records", 0); ss = s.get("statements", 0)
        mr = rec_by_c.get(n, 0)
        delta = mr - sr
        ok = ok and (delta == 0)
        tot_mirror += mr; tot_shard_r += sr; tot_stmt += ss
        for lane, cnt in lane_by_c.get(n, {}).items():
            lane_totals[lane] += cnt
        flag = "" if delta == 0 else "  <<< DELTA"
        print(f"  c{n} | {mr:>10} | {sr:>10} | {delta:>5} | {ss:>10}{flag}")
    print(f"  TOTAL | {tot_mirror:>10} | {tot_shard_r:>10} | {tot_mirror - tot_shard_r:>5} | {tot_stmt:>10}")
    print(f"  press lane split (records): {dict(lane_totals)}")

    stmt_by_c, years, ledgers = crec_pass()
    tot_crec = sum(stmt_by_c.values())
    missing_led = [n for n, present in ledgers.items() if not present]
    print("\nCREC E-LANE (the deep instrument, a SEPARATE lane; enriches, never a cross-party denominator):")
    print(f"  E-statement files: {len(years)} years ({years[0] if years else '-'}..{years[-1] if years else '-'})")
    print(f"  E-statements by Congress: {dict(sorted(stmt_by_c.items()))}")
    print(f"  total CREC E-statements: {tot_crec}")
    print(f"  ledger shards present 107-119: {'ALL' if not missing_led else 'MISSING ' + str(missing_led)}")

    ready = ok and not missing_led
    print("\n== READINESS ==")
    print(f"  press-mirror == shard inventory (delta 0 all congresses): {ok}")
    print(f"  CREC E-lane ledgers 107-119 present: {not missing_led}")
    print(f"  embeddable vector counts: press {tot_stmt} (Lane-1 normalized) + CREC {tot_crec} (E-lane)")
    print(f"  VERDICT: {'READY for the 4080 embedding pass (dry; GPU not started)' if ready else 'NOT READY - resolve deltas above'}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
