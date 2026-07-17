"""Wave S2 — full-text language-evolution hypotheses (docs/12 §S2). Aggregations over the shared
text-feature table (harness.build_text_features). Deterministic; analyzable window 113-119 (A1).

Confound discipline carried from Wave S1: every trend is a RATE (per-1k-words / per-statement), the
coverage confound is attacked first, split-halves is the CONFIRM gate, and a party-asymmetric result
triggers the power-position reframe before publication.
"""
from __future__ import annotations

import json
from collections import defaultdict
from statistics import median

from . import harness as H
from . import metrics as M
from . import provenance
from .. import config

# --- LANE ISOLATION (docs/12 L1, docs/17 §2) -----------------------------------------------------
# The old module-level halves were A=2013-2020 / B=2021-2026. That boundary IS the provenance seam:
# half A was ~95% ProPublica import, half B ~100% scraper. Every S2 verdict certified by it compared
# two INSTRUMENTS and called the difference an era. The halves below are pre-registered WITHIN one
# lane, so a split can no longer straddle 2021-01-03.
#
# The year windows also carry the brief's exclusions for free, which is why they are expressed as
# years and not as congresses: the propublica lane's 2021-01-01..03 stub (229 records) falls in year
# 2021 and so sits outside BOTH propublica halves, and the 2013-2020 scraped tail (a supplementary
# check, never pooled) sits outside both scraped halves.
LANE_HALVES: dict[str, dict[str, set]] = {
    "propublica": {"A": set(range(2013, 2017)), "B": set(range(2017, 2021))},   # 113-114 vs 115-116
    "scraped":    {"A": set(range(2021, 2024)), "B": set(range(2024, 2027))},   # 117 vs 118-119
}

# Retained ONLY so a stale caller referencing them is a loud NameError-free import rather than a
# silent seam-spanning measurement. Never use these to bucket: they are the confound.
SEAM_SPANNING_HALVES_DO_NOT_USE = {"A": set(range(2013, 2021)), "B": set(range(2021, 2027))}


def halves_for(lane: str) -> dict[str, set]:
    if lane not in LANE_HALVES:
        raise ValueError(f"no pre-registered halves for lane {lane!r} — expected one of {sorted(LANE_HALVES)}")
    return LANE_HALVES[lane]


def _half(y, halves):
    """Which pre-registered half a year falls in, or None (outside the lane's window -> excluded).
    `halves` is REQUIRED: a default here is what let the seam-spanning split travel for 34 verdicts."""
    return "A" if y in halves["A"] else ("B" if y in halves["B"] else None)


# `_load()` (a lane-blind `list(iter_text_features())`) is deliberately gone: every S2 entry point now
# takes lane-isolated rows from `load_rows(lane)`. A single un-isolated loader is exactly how the
# confound reached every hypothesis at once.


def load_rows(lane: str, *, by: str = "instrument") -> list[dict]:
    """Text-feature rows for ONE lane (docs/12 L1). `by='instrument'` folds page_html into `scraped`
    (the default — same collector); `by='source'` is the strict 3-way over raw `date_source`.

    Fails loudly on a pre-L1 cache. This matters more than it looks: `text_features.jsonl` is a
    rebuildable intermediate that is gitignored, and a cache built before the lane fields existed
    would make every filter here silently select NOTHING, which reads as an empty lane rather than a
    stale file. Every S2 hypothesis reads this table two layers below `iter_statements`, so this is
    the only place the staleness can be caught."""
    key = {"instrument": "inst", "source": "ds"}.get(by)
    if key is None:
        raise ValueError(f"by must be 'instrument' or 'source', got {by!r}")
    known = (set(provenance.INSTRUMENTS.values()) if by == "instrument" else set(provenance.DATE_SOURCES))
    if lane not in known:
        raise ValueError(f"unknown lane {lane!r} for by={by!r} — expected one of {sorted(known)}")
    rows = []
    for r in H.iter_text_features():
        if key not in r:
            raise provenance.LaneIsolationError(
                f"text_features.jsonl predates lane isolation (no {key!r} field): every S2 hypothesis "
                f"reading it is lane-blind BY SUBSTRATE. Rebuild it first — "
                f"harness.build_text_features(congresses=range(113, 120)) — see docs/17 §3.")
        if r[key] == lane:
            rows.append(r)
    return rows


# --- S2.5 Death of the Semicolon -----------------------------------------------------------------
def s2_5_semicolon(rows, *, lane, halves):
    """Semicolons per 1,000 sentences, per year. CONFIRM = >=50% decline, both halves declining.
    Within-lane (docs/17): the A->B decline is now measured inside one lane's span, so it can no
    longer be a 2013(ProPublica)->2026(scraper) instrument change wearing a trend's clothes."""
    sem, sent = defaultdict(int), defaultdict(int)
    for r in rows:
        if _half(int(r["y"]), halves):
            sem[int(r["y"])] += r["semic"]; sent[int(r["y"])] += r["ns"]
    series = [(y, 1000 * sem[y] / sent[y]) for y in sorted(sem) if sent[y]]
    a = [(y, v) for y, v in series if y in halves["A"]]
    b = [(y, v) for y, v in series if y in halves["B"]]
    early = a[0][1] if a else None
    late = b[-1][1] if b else None
    drop = (1 - late / early) if (early and late and early > 0) else None
    da, db = M.split_direction(a), M.split_direction(b)
    verdict = ("UNDERPOWERED" if len(a) < 2 or len(b) < 2 else
               "CONFIRMED" if da == -1 and db == -1 and drop and drop >= 0.50 else "REFUTED")
    return {"id": "S2.5", "name": "Death of the Semicolon", "lane": lane,
            "series": [(y, round(v, 3)) for y, v in series],
            "dir_a": da, "dir_b": db, "drop": drop and round(drop, 3), "verdict": verdict}


# --- S2.2 Adjective Inflation --------------------------------------------------------------------
def s2_2_adjective_inflation(rows, *, lane, halves):
    """Rate of each inflation-word per 1M words, per party per year. CONFIRM = >=3 of the words at
    least TRIPLE A-window -> B-window, in BOTH parties. Within-lane (docs/17)."""
    words = defaultdict(lambda: defaultdict(int))     # party -> year -> words
    cnt = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))  # party->year->term->count
    for r in rows:
        y = int(r["y"]); p = r["p"]
        if p not in ("D", "R") or _half(y, halves) is None:
            continue
        words[p][y] += r["nw"]
        for t, c in r["adj"].items():
            cnt[p][y][t] += c
    terms = list(next(iter(rows))["adj"].keys()) if rows else []
    by_party = {}
    for p in ("D", "R"):
        early_w = sum(words[p][y] for y in words[p] if y in halves["A"]) or 1
        late_w = sum(words[p][y] for y in words[p] if y in halves["B"]) or 1
        ratios = {}
        for t in terms:
            e = sum(cnt[p][y][t] for y in cnt[p] if y in halves["A"]) / early_w
            l = sum(cnt[p][y][t] for y in cnt[p] if y in halves["B"]) / late_w
            ratios[t] = round(l / e, 2) if e > 0 else None
        by_party[p] = ratios
    tripled = {p: sum(1 for t, r in by_party[p].items() if r and r >= 3.0) for p in ("D", "R")}
    verdict = "CONFIRMED" if tripled["D"] >= 3 and tripled["R"] >= 3 else "REFUTED"
    return {"id": "S2.2", "name": "Adjective Inflation", "lane": lane, "ratio_late_over_early": by_party,
            "n_tripled": tripled, "verdict": verdict}


# --- S2.7 Pronoun Economics ("I" vs "we") --------------------------------------------------------
def s2_7_pronoun(rows, *, lane, halves):
    """First-person-singular share = I / (I + we), per party per year. Reported as a trend + level;
    the 'I-season is primary-season' claim needs the election calendar (deferred). CONFIRM here = a
    stable directional trend in both halves. Within-lane (docs/17)."""
    isg, wpl = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    for r in rows:
        y = int(r["y"]); p = r["p"]
        if p in ("D", "R") and _half(y, halves):
            isg[p][y] += r["isg"]; wpl[p][y] += r["wpl"]
    out = {}
    for p in ("D", "R"):
        series = [(y, isg[p][y] / (isg[p][y] + wpl[p][y])) for y in sorted(isg[p]) if (isg[p][y] + wpl[p][y])]
        out[p] = {"series": [(y, round(v, 3)) for y, v in series],
                  "dir_a": M.split_direction([(y, v) for y, v in series if y in halves["A"]]),
                  "dir_b": M.split_direction([(y, v) for y, v in series if y in halves["B"]])}
    both = all(out[p]["dir_a"] == out[p]["dir_b"] and out[p]["dir_a"] in (1, -1) for p in ("D", "R"))
    same = out["D"]["dir_a"] == out["R"]["dir_a"]
    verdict = "CONFIRMED" if both and same else "REFUTED"
    return {"id": "S2.7", "name": "Pronoun Economics", "lane": lane, "by_party": out, "verdict": verdict}


# --- S2.10 The Concern Ladder --------------------------------------------------------------------
def s2_10_concern(rows, *, lane):
    """Frequencies of the concern ladder (concerned > deeply concerned > gravely concerned > alarmed).
    CONFIRM = the escalation ordering holds (each deeper term rarer than the shallower) across the
    corpus (a real grammar of escalation). This is a within-corpus ORDERING, not a trend, so it needs
    no half split; it is still run per-lane so a lane can never contaminate the other's counts."""
    tot = defaultdict(int)
    words = 0
    for r in rows:
        words += r["nw"]
        for t, c in r["concern"].items():
            tot[t] += c
    order = ["concerned", "deeply concerned", "gravely concerned", "alarmed"]
    rates = {t: round(1e6 * tot[t] / words, 3) for t in order} if words else {}
    # note "concerned" count includes the multiword variants; report both raw and interpretive
    monotone = all(tot[order[i]] >= tot[order[i + 1]] for i in range(len(order) - 1))
    verdict = "CONFIRMED" if monotone else "REFUTED"
    return {"id": "S2.10", "name": "The Concern Ladder", "lane": lane, "counts": dict(tot), "rate_per_1M": rates,
            "ordering_holds": monotone, "verdict": verdict,
            "note": "'concerned' subsumes the deeper multiword forms; ordering is on raw counts"}


# --- S2.12 The Apology Corpus --------------------------------------------------------------------
def s2_12_apology(rows, *, lane, halves):
    """Apology-phrase rate per 100k statements, era trend. Expected rare -> likely UNDERPOWERED; the
    null ('Congress apologizes N times per year, ~unchanged') publishes as a T3 footnote. Within-lane
    (docs/17): the power floor now applies to ONE lane's apologies, so a lane with too few is honestly
    UNDERPOWERED rather than borrowing the other lane's count."""
    ap, tot = defaultdict(int), defaultdict(int)
    for r in rows:
        if _half(int(r["y"]), halves):
            ap[int(r["y"])] += r["apol"]; tot[int(r["y"])] += 1
    series = [(y, 1e5 * ap[y] / tot[y]) for y in sorted(tot) if tot[y]]
    total_ap = sum(ap.values())
    a = [(y, v) for y, v in series if y in halves["A"]]
    b = [(y, v) for y, v in series if y in halves["B"]]
    powered = total_ap >= 100
    da, db = M.split_direction(a), M.split_direction(b)
    verdict = ("UNDERPOWERED" if not powered else "CONFIRMED" if da == db and da in (1, -1) else "REFUTED")
    return {"id": "S2.12", "name": "The Apology Corpus", "lane": lane, "total_apologies": total_ap,
            "rate_per_100k_by_year": [(y, round(v, 1)) for y, v in series], "verdict": verdict}


# --- S2.4 Punctuation Archaeology (single-artifact firsts) ---------------------------------------
def s2_4_punctuation_firsts(rows, *, lane, halves):
    """Earliest emoji and earliest ALL-CAPS-word statement (single-artifact finds; the receipt is the
    finding). Also the exclamation-rate trend. Within-lane (docs/17): the firsts are reported PER LANE
    because a 'first emoji' is a property of a collector — the ProPublica import and the scraper parse
    text differently, so the earliest emoji each surfaces is a fact about that instrument, and pooling
    them would attribute one lane's artifact to a date the other lane cannot see. The excl trend rides
    the lane's own halves."""
    first_emoji = first_caps = None
    excl, stmts = defaultdict(int), defaultdict(int)
    for r in rows:
        if r.get("emoji") and (first_emoji is None or r["d"] < first_emoji[0]):
            first_emoji = (r["d"], r["b"], r["p"])
        if r.get("caps") and (first_caps is None or r["d"] < first_caps[0]):
            first_caps = (r["d"], r["b"], r["p"])
        y = int(r["y"])
        if _half(y, halves):
            excl[y] += r["excl"]; stmts[y] += 1
    excl_series = [(y, round(excl[y] / stmts[y], 3)) for y in sorted(stmts) if stmts[y]]
    return {"id": "S2.4", "name": "Punctuation Archaeology", "lane": lane, "first_emoji": first_emoji,
            "first_allcaps": first_caps, "exclamations_per_statement_by_year": excl_series,
            "verdict": "DESCRIPTIVE"}


# --- S2.1 The Voldemort Index --------------------------------------------------------------------
def s2_1_voldemort(rows, presidents, *, lane, halves):
    """Do parties avoid NAMING the opposing president? Per year, for the sitting president: name-token
    mentions vs euphemism mentions, by party. Avoidance = euph / (name + euph). CONFIRM = the OPPOSING
    party avoids (higher euphemism share) MORE than the president's OWN party, by >=10pp, in BOTH halves
    and across presidencies with both-party data. Within-lane (docs/17)."""
    def pres_of(year):
        for t in presidents["terms"]:
            sy, ey = int(t["start"][:4]), int(t["end"][:4])
            if sy <= year < ey or (year == sy):
                # pick the term covering most of the year: seated by ~Jan 20
                if sy < year < ey:
                    return t
        # fallback: the term whose window contains mid-year
        for t in presidents["terms"]:
            if t["start"] <= f"{year}-07-01" < t["end"]:
                return t
        return None
    name_ct = defaultdict(lambda: defaultdict(int))   # year -> party -> current-pres name mentions
    euph_ct = defaultdict(lambda: defaultdict(int))
    for r in rows:
        y = int(r["y"]); p = r["p"]
        if p not in ("D", "R") or _half(y, halves) is None:
            continue
        t = pres_of(y)
        if not t:
            continue
        pres_name = t["name_tokens"][0]
        name_ct[y][p] += r["pres"].get(pres_name, 0)
        euph_ct[y][p] += r["euph"]
    rows_out = {}
    gaps = {"A": [], "B": []}
    for y in sorted(name_ct):
        t = pres_of(y)
        pres_party = t["party"]
        yr = {}
        for p in ("D", "R"):
            nm, eu = name_ct[y][p], euph_ct[y][p]
            avoid = eu / (nm + eu) if (nm + eu) else None
            yr[p] = {"name": nm, "euph": eu, "avoidance": avoid and round(avoid, 3)}
        opp = "D" if pres_party == "R" else "R"
        if yr[opp]["avoidance"] is not None and yr[pres_party]["avoidance"] is not None:
            gap = yr[opp]["avoidance"] - yr[pres_party]["avoidance"]
            yr["opp_minus_own_avoidance"] = round(gap, 3)
            gaps[_half(y, halves)].append(gap)
        yr["president"] = f"{t['name']} ({pres_party})"
        rows_out[y] = yr
    med_a = median(gaps["A"]) if gaps["A"] else None
    med_b = median(gaps["B"]) if gaps["B"] else None
    confirm = (med_a is not None and med_b is not None and med_a >= 0.10 and med_b >= 0.10)
    verdict = ("UNDERPOWERED" if (med_a is None or med_b is None) else "CONFIRMED" if confirm else "REFUTED")
    return {"id": "S2.1", "name": "The Voldemort Index", "lane": lane, "by_year": rows_out,
            "median_opp_minus_own_avoidance_A": med_a and round(med_a, 3),
            "median_opp_minus_own_avoidance_B": med_b and round(med_b, 3), "verdict": verdict}


# --- S2.3 What Losing Sounds Like (the minority's linguistic signature; power-position test) -------
def s2_3_what_losing_sounds_like(rows, chambers, roster, *, lane, halves=None, min_cell=200):
    """Markers of out-of-power rhetoric — 'the american people' rate, rhetorical-question rate,
    exclamation density (all per 1k words) — by MAJORITY vs MINORITY status (member's party controls
    their chamber?). CONFIRM (power-position, symmetric): minority > majority on >=2 of 3 markers for
    BOTH parties (it's about being out of power, not about which party). Resolves the S1.9/S1.4
    asymmetry question: is tighter/louder messaging a party trait or a minority trait?

    RE-VALIDATION (docs/17 §4.1). The original REFUTED rested on "Half A fails" with A=2013-2020 and
    B=2021-2026 — i.e. half A WAS the ProPublica lane and half B WAS the scraper lane. Its own note
    called the minority signature "a RECENT-era (2021-26) effect"; 2021-26 is not an era here, it is
    an instrument. `lane` is mandatory and `rows` must already be isolated to it: the halves now sit
    inside one lane, so a disagreement between them is a disagreement about time, not about plumbing.
    """
    halves = halves or halves_for(lane)
    got = provenance.lane_of(
        [{"date_source": r["ds"]} for r in rows if _half(int(r["y"]), halves)])
    if got is not None and got != lane:
        raise provenance.LaneIsolationError(
            f"rows are lane {got!r} but lane={lane!r} was declared — isolate with load_rows(lane) first")
    cc = chambers["by_congress"]
    markers = ["american_people", "questions", "exclamations"]
    field = {"american_people": "ampeople", "questions": "quest", "exclamations": "excl"}

    def markers_for(yrs):
        agg = defaultdict(lambda: {"w": 0, "ampeople": 0, "quest": 0, "excl": 0, "n": 0})
        for r in rows:
            p, c = r["p"], str(r["c"])
            if p not in ("D", "R") or c not in cc or int(r["y"]) not in yrs:
                continue
            ch = (roster.get(r["b"]) or {}).get("chamber")
            if ch not in ("house", "senate"):
                continue
            a = agg[(p, "maj" if cc[c][ch] == p else "min")]
            a["w"] += r["nw"]; a["n"] += 1
            for m in markers:
                a[field[m]] += r[field[m]]
        rate = {}
        for p in ("D", "R"):
            for s in ("min", "maj"):
                a = agg[(p, s)]; w = a["w"] or 1
                rate[f"{p}_{s}"] = {**{m: round(1000 * a[field[m]] / w, 3) for m in markers}, "n": a["n"]}
        return rate
    # Pooled is the LANE's own span (A|B), never a fixed 2013-2026 window: a pooled arm spanning the
    # seam is the very artifact this re-validation exists to strip.
    full = markers_for(halves["A"] | halves["B"])
    half_a = markers_for(halves["A"])
    half_b = markers_for(halves["B"])

    def party_min_higher(rate, p):   # #markers where minority > majority
        return sum(1 for m in markers if rate[f"{p}_min"][m] > rate[f"{p}_maj"][m])
    # PRE-REGISTERED GATE: minority > majority on >=2 markers, BOTH parties, BOTH halves (§S2.3).
    both_halves = all(party_min_higher(h, p) >= 2 for h in (half_a, half_b) for p in ("D", "R"))
    # Power is a per-HALF property: a pooled-only floor passes when one half carries every statement,
    # which is exactly the shape a lane-split produces.
    cells = {f"{h}:{p}_{s}": rate[f"{p}_{s}"]["n"]
             for h, rate in (("A", half_a), ("B", half_b))
             for p in ("D", "R") for s in ("min", "maj")}
    powered = all(n >= min_cell for n in cells.values())
    verdict = "UNDERPOWERED" if not powered else ("CONFIRMED" if both_halves else "REFUTED")
    return {"id": "S2.3", "name": "What Losing Sounds Like", "lane": lane,
            "halves": {k: sorted(v) for k, v in halves.items()}, "pooled": full,
            "half_A": {p: party_min_higher(half_a, p) for p in ("D", "R")},
            "half_B": {p: party_min_higher(half_b, p) for p in ("D", "R")},
            "rates_A": half_a, "rates_B": half_b, "cells": cells, "min_cell": min_cell,
            "powered": powered, "verdict": verdict}


# --- S2.6 Reading Level (sentence-complexity proxy) -----------------------------------------------
def s2_6_reading_level(rows, *, lane, halves):
    """Words-per-sentence (a readability proxy; syllables not captured), per party per year, plus the
    DC-vs-recess (August) sub-check. CONFIRM = a stable directional shift in both halves, both parties.
    Within-lane (docs/17)."""
    wps = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # party -> year -> [words, sentences]
    aug = {"aug": [0, 0], "other": [0, 0]}
    for r in rows:
        y, p = int(r["y"]), r["p"]
        if p in ("D", "R") and _half(y, halves):
            wps[p][y][0] += r["nw"]; wps[p][y][1] += r["ns"]
        mo = int(r["d"][5:7])
        k = "aug" if mo == 8 else "other"
        aug[k][0] += r["nw"]; aug[k][1] += r["ns"]
    out = {}
    for p in ("D", "R"):
        series = [(y, wps[p][y][0] / wps[p][y][1]) for y in sorted(wps[p]) if wps[p][y][1]]
        out[p] = {"series": [(y, round(v, 2)) for y, v in series],
                  "dir_a": M.split_direction([(y, v) for y, v in series if y in halves["A"]]),
                  "dir_b": M.split_direction([(y, v) for y, v in series if y in halves["B"]])}
    recess = {"aug_wps": round(aug["aug"][0] / (aug["aug"][1] or 1), 2),
              "other_wps": round(aug["other"][0] / (aug["other"][1] or 1), 2)}
    both = all(out[p]["dir_a"] == out[p]["dir_b"] and out[p]["dir_a"] in (1, -1) for p in ("D", "R"))
    verdict = "CONFIRMED" if both else "REFUTED"
    return {"id": "S2.6", "name": "Reading Level Drift", "lane": lane, "by_party": out,
            "recess_vs_dc": recess, "verdict": verdict}


def run_all(lanes=("propublica", "scraped")):
    """Every S2 hypothesis, run WITHIN each lane on that lane's pre-registered halves (docs/17 §2).
    Returns {lane: [results]}. A CONFIRM in a single lane is a within-lane confirm; a CONFIRM in BOTH
    lanes is the twice-confirmed tier. The seam-spanning `run_all()` that pooled 2013-2026 is gone —
    that pooling was the confound."""
    pres = json.load(open(config.DERIVED.parent / "reference" / "search" / "presidents.json", encoding="utf-8"))
    out = {}
    for lane in lanes:
        rows = load_rows(lane)
        halves = halves_for(lane)
        out[lane] = [
            s2_5_semicolon(rows, lane=lane, halves=halves),
            s2_2_adjective_inflation(rows, lane=lane, halves=halves),
            s2_7_pronoun(rows, lane=lane, halves=halves),
            s2_10_concern(rows, lane=lane),
            s2_12_apology(rows, lane=lane, halves=halves),
            s2_4_punctuation_firsts(rows, lane=lane, halves=halves),
            s2_1_voldemort(rows, pres, lane=lane, halves=halves),
            s2_6_reading_level(rows, lane=lane, halves=halves),
        ]
    return out
