"""Wave S2 (full-text language-evolution hypotheses) — WITHIN-LANE re-validation (docs/17 §4.3).

Runs every S2 hypothesis inside each provenance lane on that lane's pre-registered halves. The old
wave pooled 2013-2026 and split A=2013-2020 (ProPublica) / B=2021-2026 (scraper) — the seam. Here:
    propublica: A=2013-2016 vs B=2017-2020    (8 years)
    scraped:    A=2021-2023 vs B=2024-2026    (6 years, + a 2013-2020 supplementary tail, never pooled)

A within-lane CONFIRM needs the expected sign in BOTH halves of ONE lane. A both-lanes CONFIRM is the
twice-confirmed tier. Any hypothesis whose effect only appears when the window spans 2013->2026 is,
correctly, unconfirmable within a lane — that is the finding, not a failure.

Re-runnable: python scripts/search/revalidate_s2_wave.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.search import wave_s2 as S2


def main():
    by_lane = S2.run_all()
    summary = {}
    for lane, results in by_lane.items():
        print(f"\n================= lane: {lane} =================")
        for res in results:
            v = res["verdict"]
            extra = ""
            if "drop" in res:
                extra = f"  dir_a={res.get('dir_a')} dir_b={res.get('dir_b')} drop={res.get('drop')}"
            if res["id"] == "S2.2":
                extra = f"  n_tripled={res['n_tripled']}"
            if res["id"] == "S2.7":
                extra = "  " + " ".join(f"{p}:a={res['by_party'][p]['dir_a']},b={res['by_party'][p]['dir_b']}" for p in ("D", "R"))
            if res["id"] == "S2.10":
                extra = f"  ordering_holds={res['ordering_holds']} counts={res['counts']}"
            if res["id"] == "S2.12":
                extra = f"  total_apologies={res['total_apologies']}"
            if res["id"] == "S2.1":
                extra = f"  medA={res['median_opp_minus_own_avoidance_A']} medB={res['median_opp_minus_own_avoidance_B']}"
            if res["id"] == "S2.6":
                extra = "  " + " ".join(f"{p}:a={res['by_party'][p]['dir_a']},b={res['by_party'][p]['dir_b']}" for p in ("D", "R"))
            print(f"  {res['id']:6} {res['name']:26} {v:12}{extra}")
            summary.setdefault(res["id"], {})[lane] = v
    print("\n================= verdict matrix (id: propublica / scraped) =================")
    for sid in sorted(summary):
        pp = summary[sid].get("propublica", "-")
        sc = summary[sid].get("scraped", "-")
        both = "  <-- BOTH-LANES CONFIRMED" if pp == sc == "CONFIRMED" else ""
        print(f"  {sid:6} {pp:12} {sc:12}{both}")
    dest = Path(__file__).resolve().parents[2] / "data" / "derived" / "search" / "revalidate_s2_wave.json"
    dest.write_text(json.dumps(by_lane, indent=1), encoding="utf-8")
    print(f"\nwrote {dest}")
    return by_lane


if __name__ == "__main__":
    main()
