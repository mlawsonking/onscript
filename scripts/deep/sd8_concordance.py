"""SD.8 - Instrument concordance (docs/15 Wave D4, the calibration study). Frozen Session 51.

THE CALIBRATION LAW (docs/15 §0 law 2): no CREC-only pre-2013 claim publishes until its metric has
been computed on BOTH instruments over the 2013-2026 overlap and the directions AGREE. SD.8 is that
study. It runs FIRST in the Deep Annex because the law demands it, and its verdict GATES pre-2013
publication for the metric family it tests (this session performs NO publication act either way).

PRE-REGISTRATION (frozen BEFORE measurement; docs/12 §1, docs/15 §6). Committed as a registration
before the measurement commit, so no threshold is tuned after seeing data.

  * Family under test: SPEAKER-ATTRIBUTION / president-NAMING (the S2.9 "Boogeyman" family).
    This is the objectively-selected CREC-valid family, and the selection is stated, not silent:
      - docs/15 §D1-A: CREC is a WEAK carrier for phrase-COORDINATION (the S1 family) until the
        crec coordination-boilerplate layer is complete (docs/15 §9 lists 3 open residuals), so the
        S1 family has NO admissible CREC analogue yet and is EXCLUDED by pre-registration.
      - The S4 event family is largely BLOCKED (docs/13) and is EXCLUDED.
      - The S2 lexical-STYLE family (semicolons, pronouns, sentence length, apologies, ...) is
        EXCLUDED: Extensions of Remarks is a written-insertion genre with a different register, and
        several of those verdicts are directionless nulls with no sign to concord.
      - The president-NAMING metric is boilerplate-robust (name counting needs no coordination
        suppressor), direction-crisp, well-powered on CREC, and docs/13 names S2.9 as "the ancestor
        SD.2 would extend onto CREC as the twice-confirmed tier". It is the one unambiguous analogue.

  * Reference direction (press core, already verdicted): S2.9 is CONFIRMED and twice-confirmed - the
    OUT-party (the party NOT holding the White House) names the sitting president MORE than the
    in-party, EVERY year 2013-2026 (14/14; docs/13 L124/L581). Direction under test on CREC: out>in.

  * CREC metric (IDENTICAL to S2.9, re-instrumented on CREC Extensions): for each year Y in
    2013-2026, the sitting president is the presidents.json term covering Y-07-01; its name_token
    (obama|trump|biden) is counted as whole-word mentions per 1000 words, by party; the out-party is
    not-potus (chambers-control 'potus', by the modal congress of the year). Per-year CREC direction
    = (out_rate > in_rate). Rate, never count (docs/12 §1.3 coverage-confound guard).

  * Power floor (docs/12 §1.6, written as a numeral BEFORE measuring): a year is SCORED only if BOTH
    parties have >= 200 CREC Extensions statements that year. Unscored years are DISCLOSED, never
    silently dropped.

  * Frozen decision rule (numerals BEFORE measuring):
      - agreement_share    = (scored years with CREC out>in) / (scored years).
      - contradiction_share = (scored years with CREC out<in) / (scored years).  [ties are neither]
      - CONFIRM  iff scored_years >= 8 AND agreement_share >= 0.75 AND out>in is the majority
                 direction in BOTH sub-eras 2013-2020 and 2021-2026 (guards a single-era artifact).
      - REFUTE   iff contradiction_share >= 0.75 (the CREC instrument systematically shows the
                 OPPOSITE direction - in-party names the president more). A null/equal result is NOT
                 a refutation.
      - HELD     otherwise (indeterminate / mixed / null / underpowered): the parent S2.9 STANDS as
                 measured, but the CREC lane is NOT calibrated for this family and pre-2013 naming
                 claims do NOT advance to publication. HELD != REFUTED (docs/13 HX.4-D precedent).
      - ARTIFACT iff a named confound inverts the raw vs controlled direction (reported if found).

  Either outcome is a publishable methods card (docs/15 §6). Verdict GATES pre-2013 naming
  publication; it is not itself a publication.

Re-runnable:  python scripts/deep/sd8_concordance.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline import config  # noqa: E402
from pipeline.deep import crec  # noqa: E402

OVERLAP_CONGRESSES = (113, 114, 115, 116, 117, 118, 119)   # 2013-2026, the press/CREC overlap
SUB_ERA = {"2013-2020": range(2013, 2021), "2021-2026": range(2021, 2027)}
SCORE_FLOOR = 200                # >= 200 statements/party/year (docs/12 §1.6)
CONFIRM_SHARE = 0.75             # agreement (out>in) share for CONFIRM
REFUTE_CONTRA_SHARE = 0.75       # contradiction (out<in) share for REFUTE (a null is NOT a refute)
MIN_SCORED_YEARS = 8

_WORD = re.compile(r"[a-z']+")


def _mentions(low: str, token: str) -> int:
    return len(re.findall(rf"\b{re.escape(token)}\b", low))


def sitting_president(presidents: dict, year: int):
    """(name_token, party) of the president whose term covers mid-year Y-07-01 - the S2.9 rule."""
    for t in presidents["terms"]:
        if t["start"] <= f"{year}-07-01" < t["end"]:
            return t["name_tokens"][0], t["party"]
    return None, None


def concordance(statements, presidents: dict, chambers: dict, *, floor: int = SCORE_FLOOR) -> dict:
    """The frozen SD.8 metric. `statements` = CREC Extensions dicts (title/text/published_at/member/
    congress). Pure function of its inputs so the failure fixtures can drive it with a synthetic corpus."""
    cc = chambers["by_congress"]
    # year -> party -> [name_mentions, words, n_statements]; and year -> congress vote
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    year_congress = defaultdict(lambda: defaultdict(int))
    for s in statements:
        y = int(str(s["published_at"])[:4])
        p = (s.get("member") or {}).get("party")
        if p not in ("D", "R"):
            continue
        tok, _pp = sitting_president(presidents, y)
        if tok is None:
            continue
        low = ((s.get("title") or "") + " . " + (s.get("text") or "")).lower()
        agg[y][p][0] += _mentions(low, tok)
        agg[y][p][1] += len(_WORD.findall(low))
        agg[y][p][2] += 1
        if s.get("congress"):
            year_congress[y][str(s["congress"])] += 1

    per_year = {}
    for y in sorted(agg):
        cong = max(year_congress[y], key=year_congress[y].get) if year_congress[y] else None
        potus = cc.get(cong, {}).get("potus") if cong else None
        if potus not in ("D", "R"):
            continue
        out_party = "D" if potus == "R" else "R"
        rate, n = {}, {}
        for party in ("D", "R"):
            nm, w, cnt = agg[y][party]
            rate[party] = (1000.0 * nm / w) if w else None
            n[party] = cnt
        scored = n["D"] >= floor and n["R"] >= floor and rate["D"] is not None and rate["R"] is not None
        out_higher = (scored and rate[out_party] > rate[potus])
        out_lower = (scored and rate[out_party] < rate[potus])
        per_year[y] = {
            "potus_party": potus, "out_party": out_party,
            "out_rate": rate[out_party] and round(rate[out_party], 4),
            "in_rate": rate[potus] and round(rate[potus], 4),
            "n_out": n[out_party], "n_in": n[potus],
            "scored": scored, "out_higher": out_higher, "out_lower": out_lower,
        }

    scored_years = [y for y, d in per_year.items() if d["scored"]]
    agree = [y for y in scored_years if per_year[y]["out_higher"]]
    contra = [y for y in scored_years if per_year[y]["out_lower"]]
    share = (len(agree) / len(scored_years)) if scored_years else 0.0
    contra_share = (len(contra) / len(scored_years)) if scored_years else 0.0

    def sub_majority(rng):
        ys = [y for y in scored_years if y in rng]
        hi = sum(1 for y in ys if per_year[y]["out_higher"])
        return {"scored": len(ys), "out_higher": hi, "majority": (len(ys) > 0 and hi * 2 > len(ys))}

    subs = {k: sub_majority(v) for k, v in SUB_ERA.items()}
    both_eras = all(subs[k]["majority"] for k in SUB_ERA)

    if len(scored_years) >= MIN_SCORED_YEARS and share >= CONFIRM_SHARE and both_eras:
        verdict = "CONFIRM"
    elif contra_share >= REFUTE_CONTRA_SHARE:
        verdict = "REFUTE"
    else:
        verdict = "HELD"

    return {
        "id": "SD.8", "name": "Instrument concordance (president-naming family)",
        "reference": "S2.9 press-core direction out>in, 14/14 years (docs/13 L124/L581)",
        "window": "2013-2026 overlap (CREC congresses 113-119)",
        "estimator": "sitting-president name_token mentions per 1000 words, out-party vs in-party, per year",
        "floor": floor, "thresholds": {"confirm_share": CONFIRM_SHARE,
                                        "refute_contradiction_share": REFUTE_CONTRA_SHARE,
                                        "min_scored_years": MIN_SCORED_YEARS},
        "scored_years": scored_years, "years_out_higher": agree, "years_out_lower": contra,
        "agreement_share": round(share, 4), "contradiction_share": round(contra_share, 4),
        "sub_eras": subs, "both_eras_majority": both_eras,
        "verdict": verdict, "per_year": per_year,
    }


def load_crec_overlap():
    st = []
    for c in OVERLAP_CONGRESSES:
        st.extend(crec._load_statements(crec.congress_years(c)))
    return st


def main() -> int:
    presidents = json.loads((config.REFERENCE / "search" / "presidents.json").read_text(encoding="utf-8"))
    chambers = json.loads((config.REFERENCE / "search" / "chambers-control.json").read_text(encoding="utf-8"))
    statements = load_crec_overlap()
    print(f"[SD.8] loaded {len(statements):,} CREC Extensions statements over congresses "
          f"{OVERLAP_CONGRESSES[0]}-{OVERLAP_CONGRESSES[-1]}")
    res = concordance(statements, presidents, chambers)
    print(f"\n[SD.8] president-naming concordance, CREC vs press-core direction (out>in):")
    for y in sorted(res["per_year"]):
        d = res["per_year"][y]
        mark = "OK " if d["out_higher"] else ("<> " if d["scored"] else "-- ")
        print(f"  {y} potus={d['potus_party']} out={d['out_party']}  out_rate={d['out_rate']}  "
              f"in_rate={d['in_rate']}  n(out/in)={d['n_out']}/{d['n_in']}  {mark}"
              f"{'' if d['scored'] else '(UNSCORED: below floor)'}")
    print(f"\n  scored years: {len(res['scored_years'])}  out>in in {len(res['years_out_higher'])}  "
          f"share={res['agreement_share']}")
    for k, v in res["sub_eras"].items():
        print(f"    {k}: {v['out_higher']}/{v['scored']} majority={v['majority']}")
    print(f"  contradiction_share={res['contradiction_share']}")
    print(f"\n  VERDICT: {res['verdict']}  (CONFIRM: agree>={CONFIRM_SHARE} both-eras · "
          f"REFUTE: contra>={REFUTE_CONTRA_SHARE} · else HELD)")
    dest = config.DERIVED / "crec" / "sd8_concordance.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
