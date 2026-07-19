"""docs/19 §4 — THE ROBUSTNESS RIDER. Re-run the nomenclature-exposed CONFIRMED findings on
TAG-STRIPPED substrate, so a phrase-co-use finding cannot be an artifact of two offices independently
naming the same bill or committee (docs/16's core insight: bill titles manufacture co-use).

  S1.9   (weekly content-5-gram overlap, congress 117, SCRAPED lane): exclude every 5-gram whose token
         window overlaps an official-name span. Pre-registered expectation: D > R holds, D exceeds R in
         >=60% of matched weeks.
  S1.1' / S1.3'  (bursts, PROPUBLICA lane 113-116): drop any phrase that is an official name (a phrase
         whose string is covered by a name span — the string-level read of "in-congress occurrences are
         majority-tagged", used because 113-116 have no per-congress verdicts table). Pre-registered
         expectation: dir < 0 in BOTH within-lane halves AND density-survives; the ratio/drop MAY
         shrink — report both numbers.
  S2.9   EXEMPT (a president's name is not bill nomenclature).

If a gate fails, the finding is AMENDED, not suppressed, and its publication stays blocked pending
Fable (docs/19 §4). Either way a ledger row is appended.

Re-runnable:  python scripts/search/revalidate_nomenclature_rider.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline import config, nomenclature
from pipeline.search import harness as H
from pipeline.search import wave_s1 as S1

CACHE = config.DERIVED / "search"


def _phrase_is_nomenclature(ng: str, idx) -> bool:
    """String-level read of the tagger's occurrence rule: the phrase is nomenclature iff a name span
    covers it (contains it, class A, or the phrase edge truncates a name, class B). Consistent with
    nomenclature._classify — 'child tax credit' is NOT covered (the name starts at 'no'), '21st century
    road to housing act' IS. Used where no per-congress verdicts table exists (113-116)."""
    toks = ng.split()
    runs = nomenclature.name_spans(toks, idx)
    if not runs:
        return False
    return nomenclature.classify_occ(toks, 0, len(toks), runs) is not None


def run_s1_9():
    print("\n########## S1.9 — weekly 5-gram overlap, congress 117 (scraped), tag-stripped ##########")
    base = S1.s1_9_self_audit(congresses=(117,), lane="scraped", strip_nomenclature=False)
    strip = S1.s1_9_self_audit(congresses=(117,), lane="scraped", strip_nomenclature=True)
    for label, r in (("BASELINE", base), ("TAG-STRIPPED", strip)):
        wm = r.get("weeks_matched") or 0
        dgr = r.get("weeks_D_exceeds_R") or 0
        print(f"  {label:12} D overlap {r.get('mean_weekly_overlap_D')} vs R {r.get('mean_weekly_overlap_R')} "
              f"| weeks {wm} | D>R {dgr} ({100 * dgr // max(wm, 1)}%) | {r.get('direction')} -> {r.get('verdict')}")
    # pre-registered expectation: D > R AND D>R in >=60% of matched weeks
    wm = strip.get("weeks_matched") or 0
    holds = (strip.get("verdict") == "CONFIRMED"
             and (strip.get("mean_weekly_overlap_D") or 0) > (strip.get("mean_weekly_overlap_R") or 0)
             and (strip.get("weeks_D_exceeds_R") or 0) >= 0.6 * max(wm, 1))
    print(f"  => rider expectation (D>R, >=60% weeks) holds tag-stripped: {holds}")
    return {"baseline": base, "stripped": strip, "expectation_holds": holds}


def _prime(series_rows, lane, halves, cutoff):
    return {"s1_1_prime": S1.s1_1_prime_ignition(series_rows, lane=lane, halves=halves),
            "s1_3_prime": S1.s1_3_prime_lifespan(series_rows, lane=lane, halves=halves, cutoff=cutoff)}


def run_s1_1p_s1_3p():
    print("\n########## S1.1' / S1.3' — bursts, propublica lane, nomenclature phrases dropped ##########")
    lane = "propublica"
    halves = S1.year_halves_for(lane)
    cutoff = "2021-01-03"                         # docs/18 §5 lane edge
    idx = nomenclature.load_index(116)            # cumulative 108..116
    rows = list(H.iter_daily_series(lane=lane))
    kept, dropped = [], []
    for row in rows:
        (dropped if _phrase_is_nomenclature(row.get("ng", ""), idx) else kept).append(row)
    print(f"  phrases: {len(rows)} total -> dropped {len(dropped)} nomenclature, kept {len(kept)}")
    print(f"  examples dropped: {[r['ng'] for r in dropped[:6]]}")
    base = _prime(rows, lane, halves, cutoff)
    strip = _prime(kept, lane, halves, cutoff)
    out = {"dropped_count": len(dropped), "kept_count": len(kept),
           "dropped_examples": [r["ng"] for r in dropped[:20]], "baseline": {}, "stripped": {}}
    for k in ("s1_1_prime", "s1_3_prime"):
        b, s = base[k], strip[k]
        out["baseline"][k] = b
        out["stripped"][k] = s
        num = "ratio" if k == "s1_1_prime" else "median_drop"
        print(f"\n  {b['id']}  ({b['name']})")
        print(f"    BASELINE      dir_a={b['dir_a']} dir_b={b['dir_b']} {num}={b.get(num)} "
              f"density_survives={b['density_survives']} -> {b['verdict']}")
        print(f"    TAG-STRIPPED  dir_a={s['dir_a']} dir_b={s['dir_b']} {num}={s.get(num)} "
              f"density_survives={s['density_survives']} -> {s['verdict']}")
        holds = (s["dir_a"] == -1 and s["dir_b"] == -1 and bool(s["density_survives"]))
        out["stripped"][k + "_expectation_holds"] = holds
        print(f"    => rider expectation (dir<0 both halves + density-survives) holds: {holds}")
    return out


def main():
    result = {"s1_9": run_s1_9(), "s1_1p_s1_3p": run_s1_1p_s1_3p()}
    dest = CACHE / "revalidate_nomenclature_rider.json"
    dest.write_text(json.dumps(result, indent=1, default=list), encoding="utf-8")
    print(f"\nwrote {dest}")
    return result


if __name__ == "__main__":
    main()
