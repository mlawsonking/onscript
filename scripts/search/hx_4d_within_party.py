"""HX.4-D · Within-party decomposition of HX.4 — implements the frozen registration
(`data/reference/search/hx_4d-registration.json`, committed `1783987` BEFORE this run).

HX.4 found that a party's coordinated talking points persist for FEWER active days when that party
holds the House majority than when it sits in the minority (propublica r=-0.258 / scraped r=-0.380).
But propublica's majority is party-collinear (House R in 113-115, D only in 116), so there "majority"
cannot be separated from "R-ness". This decomposition asks the disaggregated question that separates
institution from party:

    Does EACH party's OWN persistence drop in the congresses where THAT party held the House majority,
    relative to the congresses where it did not?

If both parties drop (in both lanes where the floor holds), the effect is INSTITUTIONAL and HX.4's card
may proceed to review. If a powered party fails to drop, the card stays HELD (the parent number still
stands as measured; HELD is not a refutation).

  unit / persistence / lanes / statistic = IDENTICAL to HX.4 (member_index[lane] peak>=15 (phrase,
  congress) units; daily_series[lane] active-days within the congress window; calendar-span robustness;
  Mann-Whitney rank-biserial r IMPORTED from hx_4_halflife_majority so it is byte-identical).
  cell (per lane, per party P): P-MAJORITY = P units whose congress had House==P; P-MINORITY = the rest.
  gate (frozen, inherited from HX.4 unchanged): floor 200 units/cell; DROP = r<=-0.10 & p<0.05 on
  active-days AND r<0 on span; a powered non-DROP is a contradiction.
  proceed  = no powered contradiction AND a powered DROP for BOTH parties AND in BOTH lanes; else HELD.

No knob is added here. Re-runnable:
  PYTHONHASHSEED=0 C:/ProgramData/miniconda3/python.exe scripts/search/hx_4d_within_party.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))       # sibling import (hx_4_halflife_majority)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # repo root (pipeline.*)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from hx_4_halflife_majority import mann_whitney  # noqa: E402  — byte-identical statistics as the parent
from pipeline import alexandria, util  # noqa: E402
from pipeline.search import harness as H  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CHAMBERS = ROOT / "data" / "reference" / "search" / "chambers-control.json"
REG = ROOT / "data" / "reference" / "search" / "hx_4d-registration.json"
RESULT = ROOT / "scripts" / "search" / "evidence" / "hx_4d_within_party.result.json"
EVID = Path("X:/onscript-data/elections/derived")

LANES = {"propublica": range(113, 117), "scraped": range(117, 120)}
R_GATE = 0.10       # frozen (inherited from HX.4): |rank-biserial| effect-size gate
P_GATE = 0.05       # frozen
MIN_UNITS = 200     # frozen (inherited from HX.4): units per cell to be POWERED
FREEZE_COMMIT = "1783987"


def _persistence(series_row, s0, s1):
    """(active_days, calendar_span) for a phrase within a congress's [s0, s1) window — IDENTICAL to HX.4."""
    days = [d for d, _ in (series_row or ()) if s0 <= d < s1]
    if not days:
        return None
    span = (date.fromisoformat(max(days)) - date.fromisoformat(min(days))).days + 1
    return len(days), span


def measure_lane(lane, congs, control):
    ranges = {c: alexandria.congress_range(c) for c in congs}
    series = {row["ng"]: row["series"] for row in H.iter_daily_series(lane=lane)}
    # cells[party] = {"maj": [act], "min": [act], "maj_span": [...], "min_span": [...]}
    cells = {p: {"maj": [], "min": [], "maj_span": [], "min_span": []} for p in ("D", "R")}
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
        pv = _persistence(series.get(ng), s0, s1)
        if pv is None:
            continue
        persistence, span = pv
        units += 1
        bucket = "maj" if party == house else "min"
        cells[party][bucket].append(persistence)
        cells[party][f"{bucket}_span"].append(span)

    out = {"units": units, "by_party": {}}
    for p in ("D", "R"):
        maj, mino = cells[p]["maj"], cells[p]["min"]
        maj_s, min_s = cells[p]["maj_span"], cells[p]["min_span"]
        powered = len(maj) >= MIN_UNITS and len(mino) >= MIN_UNITS
        rec = {"n_maj": len(maj), "n_min": len(mino), "powered": powered}
        if powered:
            act = mann_whitney(maj, mino)          # r>0 => majority LONGER
            span = mann_whitney(maj_s, min_s)
            rec["active_days"] = act
            rec["calendar_span"] = span
            # DROP = majority persists SHORTER: r<=-0.10 & p<0.05 on active-days AND same sign on span
            is_drop = (act["rank_biserial_r"] <= -R_GATE and act["p"] < P_GATE
                       and span["rank_biserial_r"] < 0)
            rec["classification"] = "DROP" if is_drop else "CONTRADICTION"
            rec["is_drop"] = is_drop
        else:
            rec["classification"] = "UNDERPOWERED"
            rec["is_drop"] = False
        out["by_party"][p] = rec
    return out


def main():
    control = json.loads(CHAMBERS.read_text(encoding="utf-8"))["by_congress"]
    print(f"HX.4-D within-party decomposition  R_GATE={R_GATE} P_GATE={P_GATE} floor={MIN_UNITS}", flush=True)
    print(f"(frozen registration {FREEZE_COMMIT}; House: 113-115 R, 116 D, 117 D, 118-119 R)\n", flush=True)

    per_lane = {}
    for lane, congs in LANES.items():
        per_lane[lane] = measure_lane(lane, congs, control)
        print(f"  {lane}: units={per_lane[lane]['units']}", flush=True)
        for p in ("D", "R"):
            rec = per_lane[lane]["by_party"][p]
            line = f"    {p}: maj n={rec['n_maj']} / min n={rec['n_min']}  [{rec['classification']}]"
            if rec["powered"]:
                a = rec["active_days"]
                line += (f"  active-days median maj={a['median_maj']} min={a['median_min']} | "
                         f"r={a['rank_biserial_r']:+.3f} p={a['p']:.3g} | span r={rec['calendar_span']['rank_biserial_r']:+.3f}")
            print(line, flush=True)

    # ---- proceed-criterion (frozen)
    powered = [(ln, p, per_lane[ln]["by_party"][p]) for ln in LANES for p in ("D", "R")
               if per_lane[ln]["by_party"][p]["powered"]]
    drops = [(ln, p) for ln, p, rec in powered if rec["is_drop"]]
    contradictions = [(ln, p) for ln, p, rec in powered if not rec["is_drop"]]

    c1 = len(contradictions) == 0                                   # no powered contradiction
    c2 = any(p == "D" for _, p in drops) and any(p == "R" for _, p in drops)  # both parties
    c3 = any(ln == "propublica" for ln, _ in drops) and any(ln == "scraped" for ln, _ in drops)  # both lanes

    failed = []
    if not c1:
        failed.append(f"condition_1 (powered contradiction: {contradictions})")
    if not c2:
        failed.append("condition_2 (need a powered DROP for BOTH D and R)")
    if not c3:
        failed.append("condition_3 (need a powered DROP in BOTH lanes)")

    outcome = "SUPPORTS-CARD-PROCEEDS" if (c1 and c2 and c3) else "HELD"
    if outcome == "SUPPORTS-CARD-PROCEEDS":
        verdict = ("SUPPORTS-CARD-PROCEEDS — every powered within-party test drops (majority persists "
                   f"shorter); powered drops span both parties and both lanes: {drops}")
    else:
        verdict = "HELD — " + "; ".join(failed) + ". HX.4's measured effect stands; the CARD does not advance."

    print(f"\n  powered tests: {[(ln, p) for ln, p, _ in powered]}")
    print(f"  drops: {drops}")
    print(f"  conditions: no-contradiction={c1}  both-party={c2}  both-lane={c3}")
    print(f"\n===== HX.4-D OUTCOME: {outcome} =====")
    print(f"  {verdict}")

    payload = {
        "generated_at": util.now_utc_iso(),
        "registration": str(REG.relative_to(ROOT)).replace("\\", "/"),
        "registration_freeze_commit": FREEZE_COMMIT,
        "parent": {"hypothesis": "HX.4", "verdict": "CONFIRM (majority persists shorter, both lanes)"},
        "gate": {"r_gate": R_GATE, "p_gate": P_GATE, "min_units": MIN_UNITS},
        "per_lane": per_lane,
        "proceed_criterion": {
            "condition_1_no_powered_contradiction": c1,
            "condition_2_both_party_drop": c2,
            "condition_3_both_lane_drop": c3,
            "powered_tests": [[ln, p] for ln, p, _ in powered],
            "drops": [[ln, p] for ln, p in drops],
            "contradictions": [[ln, p] for ln, p in contradictions],
            "conditions_failed": failed,
        },
        "outcome": outcome,
        "verdict": verdict,
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    util.write_json(RESULT, payload)
    try:
        EVID.mkdir(parents=True, exist_ok=True)
        util.write_json(EVID / "hx_4d_within_party.result.json", payload)
    except Exception as e:
        print(f"  (evidence mirror to X: skipped: {e})", flush=True)
    print(f"wrote {RESULT}")


if __name__ == "__main__":
    main()
