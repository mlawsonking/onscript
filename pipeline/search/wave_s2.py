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
from .. import config

HALF_A = set(range(2013, 2021))
HALF_B = set(range(2021, 2027))


def _half(y):
    return "A" if y in HALF_A else ("B" if y in HALF_B else None)


def _load(feature_filter=None):
    return list(H.iter_text_features())


# --- S2.5 Death of the Semicolon -----------------------------------------------------------------
def s2_5_semicolon(rows):
    """Semicolons per 1,000 sentences, per year. CONFIRM = >=50% decline, both halves declining."""
    sem, sent = defaultdict(int), defaultdict(int)
    for r in rows:
        if _half(int(r["y"])):
            sem[int(r["y"])] += r["semic"]; sent[int(r["y"])] += r["ns"]
    series = [(y, 1000 * sem[y] / sent[y]) for y in sorted(sem) if sent[y]]
    a = [(y, v) for y, v in series if y in HALF_A]
    b = [(y, v) for y, v in series if y in HALF_B]
    early = a[0][1] if a else None
    late = b[-1][1] if b else None
    drop = (1 - late / early) if (early and late and early > 0) else None
    da, db = M.split_direction(a), M.split_direction(b)
    verdict = ("UNDERPOWERED" if len(a) < 2 or len(b) < 2 else
               "CONFIRMED" if da == -1 and db == -1 and drop and drop >= 0.50 else "REFUTED")
    return {"id": "S2.5", "name": "Death of the Semicolon", "series": [(y, round(v, 3)) for y, v in series],
            "dir_a": da, "dir_b": db, "drop": drop and round(drop, 3), "verdict": verdict}


# --- S2.2 Adjective Inflation --------------------------------------------------------------------
def s2_2_adjective_inflation(rows):
    """Rate of each inflation-word per 1M words, per party per year. CONFIRM = >=3 of the words at
    least TRIPLE A-window -> B-window, in BOTH parties."""
    words = defaultdict(lambda: defaultdict(int))     # party -> year -> words
    cnt = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))  # party->year->term->count
    for r in rows:
        y = int(r["y"]); p = r["p"]
        if p not in ("D", "R") or _half(y) is None:
            continue
        words[p][y] += r["nw"]
        for t, c in r["adj"].items():
            cnt[p][y][t] += c
    terms = list(next(iter(rows))["adj"].keys()) if rows else []
    by_party = {}
    for p in ("D", "R"):
        early_w = sum(words[p][y] for y in words[p] if y in HALF_A) or 1
        late_w = sum(words[p][y] for y in words[p] if y in HALF_B) or 1
        ratios = {}
        for t in terms:
            e = sum(cnt[p][y][t] for y in cnt[p] if y in HALF_A) / early_w
            l = sum(cnt[p][y][t] for y in cnt[p] if y in HALF_B) / late_w
            ratios[t] = round(l / e, 2) if e > 0 else None
        by_party[p] = ratios
    tripled = {p: sum(1 for t, r in by_party[p].items() if r and r >= 3.0) for p in ("D", "R")}
    verdict = "CONFIRMED" if tripled["D"] >= 3 and tripled["R"] >= 3 else "REFUTED"
    return {"id": "S2.2", "name": "Adjective Inflation", "ratio_late_over_early": by_party,
            "n_tripled": tripled, "verdict": verdict}


# --- S2.7 Pronoun Economics ("I" vs "we") --------------------------------------------------------
def s2_7_pronoun(rows):
    """First-person-singular share = I / (I + we), per party per year. Reported as a trend + level;
    the 'I-season is primary-season' claim needs the election calendar (deferred). CONFIRM here = a
    stable directional trend in both halves."""
    isg, wpl = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    for r in rows:
        y = int(r["y"]); p = r["p"]
        if p in ("D", "R") and _half(y):
            isg[p][y] += r["isg"]; wpl[p][y] += r["wpl"]
    out = {}
    for p in ("D", "R"):
        series = [(y, isg[p][y] / (isg[p][y] + wpl[p][y])) for y in sorted(isg[p]) if (isg[p][y] + wpl[p][y])]
        out[p] = {"series": [(y, round(v, 3)) for y, v in series],
                  "dir_a": M.split_direction([(y, v) for y, v in series if y in HALF_A]),
                  "dir_b": M.split_direction([(y, v) for y, v in series if y in HALF_B])}
    both = all(out[p]["dir_a"] == out[p]["dir_b"] and out[p]["dir_a"] in (1, -1) for p in ("D", "R"))
    same = out["D"]["dir_a"] == out["R"]["dir_a"]
    verdict = "CONFIRMED" if both and same else "REFUTED"
    return {"id": "S2.7", "name": "Pronoun Economics", "by_party": out, "verdict": verdict}


# --- S2.10 The Concern Ladder --------------------------------------------------------------------
def s2_10_concern(rows):
    """Frequencies of the concern ladder (concerned > deeply concerned > gravely concerned > alarmed).
    CONFIRM = the escalation ordering holds (each deeper term rarer than the shallower) across the
    corpus (a real grammar of escalation)."""
    tot = defaultdict(int)
    words = 0
    for r in rows:
        words += r["nw"]
        for t, c in r["concern"].items():
            tot[t] += c
    order = ["concerned", "deeply concerned", "gravely concerned", "alarmed"]
    rates = {t: round(1e6 * tot[t] / words, 3) for t in order}
    # note "concerned" count includes the multiword variants; report both raw and interpretive
    monotone = all(tot[order[i]] >= tot[order[i + 1]] for i in range(len(order) - 1))
    verdict = "CONFIRMED" if monotone else "REFUTED"
    return {"id": "S2.10", "name": "The Concern Ladder", "counts": dict(tot), "rate_per_1M": rates,
            "ordering_holds": monotone, "verdict": verdict,
            "note": "'concerned' subsumes the deeper multiword forms; ordering is on raw counts"}


# --- S2.12 The Apology Corpus --------------------------------------------------------------------
def s2_12_apology(rows):
    """Apology-phrase rate per 100k statements, era trend. Expected rare -> likely UNDERPOWERED; the
    null ('Congress apologizes N times per year, ~unchanged') publishes as a T3 footnote."""
    ap, tot = defaultdict(int), defaultdict(int)
    for r in rows:
        if _half(int(r["y"])):
            ap[int(r["y"])] += r["apol"]; tot[int(r["y"])] += 1
    series = [(y, 1e5 * ap[y] / tot[y]) for y in sorted(tot) if tot[y]]
    total_ap = sum(ap.values())
    a = [(y, v) for y, v in series if y in HALF_A]
    b = [(y, v) for y, v in series if y in HALF_B]
    powered = total_ap >= 100
    da, db = M.split_direction(a), M.split_direction(b)
    verdict = ("UNDERPOWERED" if not powered else "CONFIRMED" if da == db and da in (1, -1) else "REFUTED")
    return {"id": "S2.12", "name": "The Apology Corpus", "total_apologies": total_ap,
            "rate_per_100k_by_year": [(y, round(v, 1)) for y, v in series], "verdict": verdict}


# --- S2.4 Punctuation Archaeology (single-artifact firsts) ---------------------------------------
def s2_4_punctuation_firsts(rows):
    """Earliest emoji and earliest ALL-CAPS-word statement in the corpus (single-artifact finds; the
    receipt is the finding). Also the exclamation-rate trend."""
    first_emoji = first_caps = None
    excl, stmts = defaultdict(int), defaultdict(int)
    for r in rows:
        if r.get("emoji") and (first_emoji is None or r["d"] < first_emoji[0]):
            first_emoji = (r["d"], r["b"], r["p"])
        if r.get("caps") and (first_caps is None or r["d"] < first_caps[0]):
            first_caps = (r["d"], r["b"], r["p"])
        y = int(r["y"])
        if _half(y):
            excl[y] += r["excl"]; stmts[y] += 1
    excl_series = [(y, round(excl[y] / stmts[y], 3)) for y in sorted(stmts) if stmts[y]]
    return {"id": "S2.4", "name": "Punctuation Archaeology", "first_emoji": first_emoji,
            "first_allcaps": first_caps, "exclamations_per_statement_by_year": excl_series,
            "verdict": "DESCRIPTIVE"}


# --- S2.1 The Voldemort Index --------------------------------------------------------------------
def s2_1_voldemort(rows, presidents):
    """Do parties avoid NAMING the opposing president? Per year, for the sitting president: name-token
    mentions vs euphemism mentions, by party. Avoidance = euph / (name + euph). CONFIRM = the OPPOSING
    party avoids (higher euphemism share) MORE than the president's OWN party, by >=10pp, in BOTH halves
    and across presidencies with both-party data."""
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
        if p not in ("D", "R") or _half(y) is None:
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
            gaps[_half(y)].append(gap)
        yr["president"] = f"{t['name']} ({pres_party})"
        rows_out[y] = yr
    med_a = median(gaps["A"]) if gaps["A"] else None
    med_b = median(gaps["B"]) if gaps["B"] else None
    confirm = (med_a is not None and med_b is not None and med_a >= 0.10 and med_b >= 0.10)
    verdict = ("UNDERPOWERED" if (med_a is None or med_b is None) else "CONFIRMED" if confirm else "REFUTED")
    return {"id": "S2.1", "name": "The Voldemort Index", "by_year": rows_out,
            "median_opp_minus_own_avoidance_A": med_a and round(med_a, 3),
            "median_opp_minus_own_avoidance_B": med_b and round(med_b, 3), "verdict": verdict}


def run_all():
    rows = _load()
    pres = json.load(open(config.DERIVED.parent / "reference" / "search" / "presidents.json", encoding="utf-8"))
    return [s2_5_semicolon(rows), s2_2_adjective_inflation(rows), s2_7_pronoun(rows),
            s2_10_concern(rows), s2_12_apology(rows), s2_4_punctuation_firsts(rows),
            s2_1_voldemort(rows, pres)]
