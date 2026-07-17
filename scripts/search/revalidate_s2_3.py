"""S2.3 "What Losing Sounds Like" — WITHIN-LANE re-validation (docs/17 §4.1).

THE QUESTION. S2.3 is the program's flagship reversal: a pooled CONFIRMED that split-halves knocked
down to REFUTED, and the ledger holds it up as proof the control works. Its kill rests entirely on
"Half A fails" — and half A (2013-2020) is the ProPublica lane while half B (2021-2026) is the
scraper lane. Its own docstring called the minority signature "a RECENT-era (2021-26) effect"; that
window is not an era, it is an instrument. So the kill may be plumbing, and if it is, the ledger's
best evidence that its control works is itself a lane artifact.

WHAT THIS RUNS. The pre-registered gate, unchanged (minority > majority on >=2 of 3 markers, BOTH
parties, BOTH halves), inside ONE lane at a time, on the brief's pre-registered within-lane halves:
    propublica: A=2013-2016 vs B=2017-2020      (113-114 vs 115-116)
    scraped:    A=2021-2023 vs B=2024-2026      (117 vs 118-119)

PRE-REGISTERED FLOOR (L4 — written before the measurement, as a numeral): min_cell = 200 statements
per (half x party x majority-status) cell — the original spec's floor, now applied PER HALF rather
than pooled. Pooled-only power passes when one half carries every statement, which is exactly the
shape a lane split produces.

Re-runnable: python scripts/search/revalidate_s2_3.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline import config, roster as R
from pipeline.search import wave_s2 as S2

MIN_CELL = 200   # pre-registered, before measurement (docs/17 §2 L4)


def main():
    chambers = json.loads((config.REFERENCE / "search" / "chambers-control.json").read_text(encoding="utf-8"))
    roster = R.load()
    out = {}
    for lane in ("propublica", "scraped"):
        rows = S2.load_rows(lane)
        res = S2.s2_3_what_losing_sounds_like(rows, chambers, roster, lane=lane, min_cell=MIN_CELL)
        out[lane] = res
        h = res["halves"]
        print(f"\n=== {lane}  A={h['A'][0]}-{h['A'][-1]}  B={h['B'][0]}-{h['B'][-1]}  ({len(rows)} rows) ===")
        print(f"  markers where minority > majority (gate: >=2 for BOTH parties in BOTH halves)")
        print(f"    half A: D={res['half_A']['D']}/3  R={res['half_A']['R']}/3")
        print(f"    half B: D={res['half_B']['D']}/3  R={res['half_B']['R']}/3")
        print(f"  per-cell N (floor {MIN_CELL}): {res['cells']}")
        print(f"  powered={res['powered']}  VERDICT={res['verdict']}")
        for half, rates in (("A", res["rates_A"]), ("B", res["rates_B"])):
            print(f"  --- rates per 1k words, half {half} ---")
            for p in ("D", "R"):
                for s in ("min", "maj"):
                    c = rates[f"{p}_{s}"]
                    print(f"    {p}_{s}: ampeople={c['american_people']:>6}  quest={c['questions']:>6}"
                          f"  excl={c['exclamations']:>6}  (n={c['n']})")
    dest = Path(__file__).resolve().parents[2] / "data" / "derived" / "search" / "revalidate_s2_3.json"
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {dest}")
    return out


if __name__ == "__main__":
    main()
