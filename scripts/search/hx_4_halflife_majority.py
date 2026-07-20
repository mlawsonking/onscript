"""HX.4 · Phrase half-life x majority status — implements the frozen registration (docs/13, committed
`bc4d0d1` BEFORE this run). Does a party sustain its coordinated talking points LONGER when it holds
the House majority than when it does not? Symmetric by construction (House control flips between
parties); within-lane only (L1). No knob is added here.

  unit         = a (phrase, congress) with peak_units>=15 (member_index[lane]); party = peak_party
  persistence  = distinct ACTIVE DAYS the phrase was used within that congress's date range
                 (daily_series[lane] filtered to [congress_start, congress_end)); primary metric,
                 calendar-span reported as robustness
  majority     = the phrase's party held the HOUSE majority that congress (chambers-control)
  gate         = per lane, Mann-Whitney U on persistence (majority vs minority units);
                 CONFIRM iff |rank-biserial r|>=0.10 & p<0.05 & same direction BOTH lanes;
                 REFUTE iff |r|<0.10 in a well-powered lane; floor 200 units/cell.

Re-runnable:  PYTHONHASHSEED=0 C:/ProgramData/miniconda3/python.exe scripts/search/hx_4_halflife_majority.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import alexandria, util  # noqa: E402
from pipeline.search import harness as H  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CHAMBERS = ROOT / "data" / "reference" / "search" / "chambers-control.json"
RESULT = ROOT / "scripts" / "search" / "evidence" / "hx_4_halflife_majority.result.json"
EVID = Path("X:/onscript-data/elections/derived")
LANES = {"propublica": range(113, 117), "scraped": range(117, 120)}
R_GATE = 0.10       # frozen: |rank-biserial| effect-size gate
P_GATE = 0.05
MIN_UNITS = 200     # frozen: units per cell to report


def _rankdata(a):
    a = np.asarray(a, float); n = len(a)
    order = np.argsort(a, kind="mergesort"); ranks = np.empty(n, float); i = 0
    tie_sizes = []
    while i < n:
        j = i
        while j + 1 < n and a[order[j + 1]] == a[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        tie_sizes.append(j - i + 1)
        i = j + 1
    return ranks, tie_sizes


def _norm_sf(z):  # upper tail of the standard normal
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def mann_whitney(maj, mino):
    """U for `maj`, rank-biserial r (r>0 => maj larger), two-sided p (tie-corrected normal approx)."""
    n1, n2 = len(maj), len(mino)
    N = n1 + n2
    ranks, ties = _rankdata(list(maj) + list(mino))
    R1 = float(ranks[:n1].sum())
    U1 = R1 - n1 * (n1 + 1) / 2.0
    r = 2.0 * U1 / (n1 * n2) - 1.0
    mu = n1 * n2 / 2.0
    tie_term = sum(t ** 3 - t for t in ties)
    var = (n1 * n2 / 12.0) * ((N + 1) - tie_term / (N * (N - 1))) if N > 1 else 0.0
    z = (U1 - mu) / math.sqrt(var) if var > 0 else 0.0
    p = 2.0 * _norm_sf(abs(z))
    return {"n_maj": n1, "n_min": n2, "U": U1, "rank_biserial_r": round(r, 4),
            "z": round(z, 3), "p": p,
            "median_maj": median(maj) if maj else None, "median_min": median(mino) if mino else None,
            "mean_maj": round(sum(maj) / n1, 2) if n1 else None,
            "mean_min": round(sum(mino) / n2, 2) if n2 else None}


def main():
    control = json.loads(CHAMBERS.read_text(encoding="utf-8"))["by_congress"]
    print(f"HX.4 half-life x majority (House proxy)  R_GATE={R_GATE} floor={MIN_UNITS}\n", flush=True)

    per_lane = {}
    for lane, congs in LANES.items():
        ranges = {c: alexandria.congress_range(c) for c in congs}
        # daily_series[lane] -> {ng: [[date,count],...]}
        series = {row["ng"]: row["series"] for row in H.iter_daily_series(lane=lane)}
        maj, mino = [], []           # persistence values by majority position
        maj_span, mino_span = [], []
        units = skipped = 0
        for row in H.iter_member_index(lane=lane):
            ng, c, party = row["ng"], row.get("congress"), row.get("peak_party")
            if c not in ranges or party not in ("D", "R"):
                continue
            house = control.get(str(c), {}).get("house")
            if house not in ("D", "R"):
                skipped += 1
                continue
            s0, s1 = ranges[c]
            days = [d for d, _ in series.get(ng, ()) if s0 <= d < s1]
            if not days:
                continue
            persistence = len(days)
            span = (__import__("datetime").date.fromisoformat(max(days))
                    - __import__("datetime").date.fromisoformat(min(days))).days + 1
            units += 1
            if party == house:
                maj.append(persistence); maj_span.append(span)
            else:
                mino.append(persistence); mino_span.append(span)
        powered = len(maj) >= MIN_UNITS and len(mino) >= MIN_UNITS
        res = mann_whitney(maj, mino) if powered else {"n_maj": len(maj), "n_min": len(mino)}
        span_res = mann_whitney(maj_span, mino_span) if powered else None
        per_lane[lane] = {"units": units, "powered": powered, "active_days": res,
                          "calendar_span_robustness": span_res}
        print(f"  {lane}: units={units} (maj {len(maj)} / min {len(mino)}) powered={powered}", flush=True)
        if powered:
            print(f"    active-days: median maj={res['median_maj']} min={res['median_min']} | "
                  f"mean maj={res['mean_maj']} min={res['mean_min']} | r={res['rank_biserial_r']} "
                  f"p={res['p']:.3g}", flush=True)
            print(f"    span robustness: r={span_res['rank_biserial_r']} p={span_res['p']:.3g}", flush=True)

    # ---- verdict (frozen gate)
    powered_lanes = [ln for ln, v in per_lane.items() if v["powered"]]
    rs = {ln: per_lane[ln]["active_days"]["rank_biserial_r"] for ln in powered_lanes}
    ps = {ln: per_lane[ln]["active_days"]["p"] for ln in powered_lanes}
    if len(powered_lanes) == 2:
        a, b = powered_lanes
        both_sig = ps[a] < P_GATE and ps[b] < P_GATE
        both_big = abs(rs[a]) >= R_GATE and abs(rs[b]) >= R_GATE
        same_dir = (rs[a] > 0) == (rs[b] > 0)
        if both_big and both_sig and same_dir:
            verdict = (f"CONFIRM — majority-party phrases persist {'LONGER' if rs[a] > 0 else 'SHORTER'} "
                       f"in BOTH lanes (r={rs[a]:+.3f}/{rs[b]:+.3f}, both p<0.05)")
        elif any(abs(rs[ln]) < R_GATE for ln in powered_lanes):
            verdict = f"REFUTE — |r|<0.10 in a well-powered lane (r={rs[a]:+.3f}/{rs[b]:+.3f})"
        else:
            verdict = f"MIXED — powered, |r|>=0.10, but signs differ or p>=0.05 (r={rs[a]:+.3f}/{rs[b]:+.3f})"
    else:
        verdict = f"UNDERPOWERED — only {len(powered_lanes)} lane(s) cleared the {MIN_UNITS}/cell floor"

    print(f"\n===== HX.4 VERDICT: {verdict} =====")
    payload = {"generated_at": util.now_utc_iso(), "registration_commit": "bc4d0d1",
               "gate": {"r_gate": R_GATE, "p_gate": P_GATE, "min_units": MIN_UNITS},
               "per_lane": per_lane, "verdict": verdict}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    util.write_json(RESULT, payload)
    EVID.mkdir(parents=True, exist_ok=True)
    util.write_json(EVID / "hx_4_halflife_majority.result.json", payload)
    print(f"wrote {RESULT}")


if __name__ == "__main__":
    main()
