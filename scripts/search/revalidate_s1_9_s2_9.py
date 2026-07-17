"""S1.9 (the 2022 Self-Audit) and S2.9 (the Boogeyman) — WITHIN-LANE re-affirmation (docs/17 §4.2).

These are the program's ONLY two CONFIRMED findings. Both were certified against a both-halves
control whose split sat on the 2021-01-03 provenance seam, so both need re-affirming within one lane
before they can keep their pedigree.

S1.9 — congress 117 (2021-22). The brief calls it "lane-clean by construction"; it is 99.6% clean.
144 ProPublica-import records dated exactly 2021-01-03 (the import's last day == the 117th's first
day) fall in congress 117. We run it BOTH ways — full 117, and 117 restricted to the scraped lane —
and report both. If the CONFIRMED verdict is identical, the finding is re-affirmed AND the "by
construction" claim is corrected to "99.6%, exclusion is a no-op". Pre-registered decision rule
(unchanged from the original): CONFIRMED iff mean weekly D overlap > R AND D exceeds R in >60% of
matched weeks.

S2.9 — the sitting-president naming rate, out-party vs in-party, per year. The original CONFIRMED was
"14/14 years, half A 8/8, half B 6/6" with A=2013-2020 (propublica) and B=2021-2026 (scraped) — the
seam split again. The finding has NO implementation in the repo (it was measured by a fan-out and only
the card survives), so this script re-implements it from the card's stated metric and runs the
both-halves gate WITHIN each lane on the pre-registered within-lane halves (docs/17 §2). A both-lanes
CONFIRM is the new twice-confirmed tier the brief describes.

Re-runnable: python scripts/search/revalidate_s1_9_s2_9.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline import config
from pipeline.search import harness as H
from pipeline.search import wave_s1 as S1
from pipeline.search import wave_s2 as S2


# ------------------------------------------------------------------ S1.9
def run_s1_9():
    print("\n########## S1.9 — The 2022 Self-Audit ##########")
    full = S1.s1_9_self_audit(congresses=(117,), lane=None)
    scraped = S1.s1_9_self_audit(congresses=(117,), lane="scraped")
    for label, res in (("congress 117 FULL (144 legacy records included)", full),
                       ("congress 117 SCRAPED-ONLY (legacy 2021-01-03 excluded)", scraped)):
        print(f"\n  {label}")
        print(f"    D weekly overlap {res['mean_weekly_overlap_D']} vs R {res['mean_weekly_overlap_R']}")
        print(f"    weeks matched {res['weeks_matched']}, D>R in {res['weeks_D_exceeds_R']} "
              f"({100*res['weeks_D_exceeds_R']//max(res['weeks_matched'],1)}%)")
        print(f"    direction {res['direction']}  ->  VERDICT {res['verdict']}")
    agree = full["verdict"] == scraped["verdict"] == "CONFIRMED"
    print(f"\n  => both runs CONFIRMED and agree: {agree}  "
          f"(exclusion is a {'no-op' if agree else 'CHANGE — investigate'})")
    return {"full": full, "scraped_only": scraped, "reaffirmed": agree}


# ------------------------------------------------------------------ S2.9
_PRES_TOKENS = {"obama": "obama", "trump": "trump", "biden": "biden"}


def _s2_9_for_lane(lane, presidents, chambers):
    """The Boogeyman, re-implemented from the S2.9 card's metric, within ONE lane.

    Metric: for the SITTING president each year, name-token mentions per 1k words, by party. The
    out-party is whoever does NOT hold the White House that year (chambers-control 'potus'); avoidance
    is not the axis — NAMING is. CONFIRM (per lane): the out-party names the sitting president more
    than the in-party (ratio > 1) in EVERY year of BOTH pre-registered halves.
    """
    halves = S2.halves_for(lane)
    cc = chambers["by_congress"]
    rows = S2.load_rows(lane)

    def potus_party(year, congress):
        c = str(congress)
        return cc.get(c, {}).get("potus")

    def pres_token_for(year):
        # the president whose term covers mid-year (matches the card's per-year sitting-president rule)
        for t in presidents["terms"]:
            if t["start"] <= f"{year}-07-01" < t["end"]:
                return t["name_tokens"][0], t["party"]
        return None, None

    # year -> party -> [name_mentions, words]
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in rows:
        y = int(r["y"]); p = r["p"]
        if p not in ("D", "R"):
            continue
        tok, _pp = pres_token_for(y)
        if tok is None:
            continue
        agg[y][p][0] += r["pres"].get(tok, 0)
        agg[y][p][1] += r["nw"]

    per_year = {}
    for y in sorted(agg):
        pp = potus_party(y, None)
        # potus is keyed by congress in chambers-control; resolve congress from the year via any row
        # (all rows in a year share the same sitting president; use the modal congress that year)
        congs = defaultdict(int)
        for r in rows:
            if int(r["y"]) == y and r["p"] in ("D", "R"):
                congs[str(r["c"])] += 1
        cong = max(congs, key=congs.get) if congs else None
        pp = cc.get(cong, {}).get("potus") if cong else None
        if pp not in ("D", "R"):
            continue
        out_party = "D" if pp == "R" else "R"
        rate = {}
        for party in ("D", "R"):
            nm, w = agg[y][party]
            rate[party] = (1000.0 * nm / w) if w else None
        if rate["D"] is None or rate["R"] is None or rate[pp] == 0:
            ratio = None
        else:
            ratio = rate[out_party] / rate[pp] if rate[pp] else None
        per_year[y] = {"potus_party": pp, "out_party": out_party,
                       "out_rate": rate[out_party] and round(rate[out_party], 4),
                       "in_rate": rate[pp] and round(rate[pp], 4),
                       "out_over_in": ratio and round(ratio, 3),
                       "half": S2._half(y, halves)}

    def half_years(h):
        return [y for y in per_year if per_year[y]["half"] == h]

    counts = {}
    for h in ("A", "B"):
        ys = half_years(h)
        out_higher = sum(1 for y in ys if (per_year[y]["out_over_in"] or 0) > 1.0)
        counts[h] = {"years": len(ys), "out_higher": out_higher,
                     "year_list": sorted(ys)}
    both = (counts["A"]["years"] > 0 and counts["B"]["years"] > 0 and
            counts["A"]["out_higher"] == counts["A"]["years"] and
            counts["B"]["out_higher"] == counts["B"]["years"])
    verdict = "CONFIRMED" if both else ("UNDERPOWERED" if not (counts["A"]["years"] and counts["B"]["years"]) else "REFUTED")
    return {"lane": lane, "halves": {k: sorted(v) for k, v in halves.items()},
            "per_year": per_year, "half_counts": counts, "verdict": verdict}


def run_s2_9():
    print("\n########## S2.9 — The Boogeyman ##########")
    presidents = json.loads((config.REFERENCE / "search" / "presidents.json").read_text(encoding="utf-8"))
    chambers = json.loads((config.REFERENCE / "search" / "chambers-control.json").read_text(encoding="utf-8"))
    out = {}
    for lane in ("propublica", "scraped"):
        res = _s2_9_for_lane(lane, presidents, chambers)
        out[lane] = res
        print(f"\n  --- {lane} ---")
        for y, d in res["per_year"].items():
            print(f"    {y} potus={d['potus_party']} out={d['out_party']}  "
                  f"out_rate={d['out_rate']}  in_rate={d['in_rate']}  out/in={d['out_over_in']}  [{d['half']}]")
        print(f"    half A: {res['half_counts']['A']['out_higher']}/{res['half_counts']['A']['years']}  "
              f"half B: {res['half_counts']['B']['out_higher']}/{res['half_counts']['B']['years']}  "
              f"-> {res['verdict']}")
    both_lanes = all(out[l]["verdict"] == "CONFIRMED" for l in ("propublica", "scraped"))
    print(f"\n  => both-lanes CONFIRMED (the twice-confirmed tier): {both_lanes}")
    out["both_lanes_confirmed"] = both_lanes
    return out


def main():
    result = {"s1_9": run_s1_9(), "s2_9": run_s2_9()}
    dest = Path(__file__).resolve().parents[2] / "data" / "derived" / "search" / "revalidate_s1_9_s2_9.json"
    dest.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"\nwrote {dest}")
    return result


if __name__ == "__main__":
    main()
