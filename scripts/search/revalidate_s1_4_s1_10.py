"""S1.4 (Copy-Paste Caucus, verbatim floor) and S1.10 (Bipartisanship Has a Season) — the two
within-lane-RUNNABLE S1 rescopes (docs/17 §3 "runnable now", §4.3).

S1.4 verbatim reads iter_statements directly (no shards), so it is runnable within a lane. Its
`_proper` density-controlled sibling reads alexandria.load_congress_records, which is lane-blind
(docs/17 §amend-3) — that arm is BLOCKED-ON-SHARDS and is NOT re-run here. Original S1.4 verdict:
REFUTED (asymmetric — D rises both halves, R rises then falls), on the seam split. Re-run within each
lane on that lane's within-lane year halves.

S1.10's defect is not a half split but per-cycle seam straddling: each cycle is a before/after
comparison across an anchor date, and the real 2020 cycle's ±90-day window (2020-08-06..2021-02-02)
straddles 2021-01-03 — its BEFORE is ProPublica, its AFTER is scraper. Dropping every seam-straddling
cycle (2020 real, 2021 placebo) leaves each surviving cycle single-lane end-to-end (2014/2016/2018 =
propublica, 2022/2024 = scraper), so the electoral-vs-seasonal comparison no longer crosses an
instrument change. The placebo runs on the SAME statistic (L3). Original verdict: ARTIFACT (placebo
troughs too -> seasonal, not electoral).

PRE-REGISTERED FLOORS (L4, before measurement):
  S1.4: >=200 statements per party per in-window year (unchanged from spec).
  S1.10: >=4 real cycles with both windows non-empty; trough in a strict majority.

Re-runnable: python scripts/search/revalidate_s1_4_s1_10.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline import config
from pipeline.search import wave_s1 as S1


def run_s1_4():
    print("\n########## S1.4 — The Copy-Paste Caucus (verbatim floor), within lane ##########")
    out = {}
    for lane in ("propublica", "scraped"):
        res = S1.s1_4_verbatim(lane=lane)
        out[lane] = res
        print(f"\n  --- {lane} (halves {sorted(S1.LANE_YEAR_HALVES[lane]['A'])} vs "
              f"{sorted(S1.LANE_YEAR_HALVES[lane]['B'])}) ---")
        for y, d in res["share_by_year"].items():
            print(f"    {y}: D={d['D']}  R={d['R']}")
        print(f"    directions {res['directions']}  ->  {res['verdict']}")
    return out


def run_s1_10():
    print("\n########## S1.10 — Bipartisanship Has a Season (seam cycles dropped) ##########")
    elections = json.loads((config.REFERENCE / "search" / "elections.json").read_text(encoding="utf-8"))["general"]
    # lane=None: every surviving cycle is single-lane by construction once the straddlers are dropped,
    # so we keep all cycles (5 real, 6 placebo) rather than starve each lane below its cycle floor.
    res = S1.s1_10_bipartisan_season(elections, lane=None)
    print(f"  dropped seam-straddling cycles: {res['dropped_seam_cycles']}")
    print(f"  real cycles (year: pre_rate -> post_rate, trough):")
    for y, c in res["cycles"].items():
        print(f"    {y}: {c['pre_rate']} -> {c['post_rate']}  trough={c['trough']}  (n {c['pre_n']}/{c['post_n']})")
    print(f"  placebo cycles:")
    for y, c in res["placebo"].items():
        print(f"    {y}: {c['pre_rate']} -> {c['post_rate']}  trough={c['trough']}  (n {c['pre_n']}/{c['post_n']})")
    print(f"  real troughs {res['real_troughs']}  placebo troughs {res['placebo_troughs']}  ->  {res['verdict']}")
    print(f"  confound: {res['confound']}")
    return res


def main():
    result = {"s1_4": run_s1_4(), "s1_10": run_s1_10()}
    dest = Path(__file__).resolve().parents[2] / "data" / "derived" / "search" / "revalidate_s1_4_s1_10.json"
    dest.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"\nwrote {dest}")
    return result


if __name__ == "__main__":
    main()
