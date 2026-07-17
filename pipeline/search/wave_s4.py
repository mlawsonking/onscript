"""Wave S4 — event-series hypotheses (docs/12 §S4). S4.1 "One Court, Two Languages":
for ~10-12 landmark SCOTUS decisions 2013-2026, measure each party's same-week response —
response volume, latency, top framing phrases, and the case-name-vs-outcome (celebration vs
condemnation) framing split.

Deterministic, stdlib-only. Reads landmarks + the pre-registered framing lexicon from
data/reference/search/scotus-landmarks.json (dates public-record verified). Statements are
selected by stance-NEUTRAL case anchors applied IDENTICALLY to both parties (symmetric
instrument). Per-case output is DESCRIPTIVE (a drip card each); the aggregate is CONFIRMED only
if a stable PARTY framing-split direction holds across >=8 cases in BOTH halves — otherwise the
split tracks who-won (a valence/power effect), which is flagged, not published as a party law.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from . import harness as H
from .. import boilerplate as B
from .. import config, fetch, util

_PARTY = {"Democrat": "D", "Republican": "R", "Independent": "I"}
REF = config.DERIVED.parent / "reference" / "search" / "scotus-landmarks.json"


def load_ref() -> dict:
    return json.load(open(REF, encoding="utf-8"))


def _needed_months(cases, window: int) -> set:
    months = set()
    for c in cases:
        d0 = date.fromisoformat(c["date"])
        for k in range(0, window + 1):
            d = d0 + timedelta(days=k)
            months.add(f"{d.year:04d}-{d.month:02d}")
    return months


def _content_ngrams(text: str, lo=2, hi=4):
    """Boilerplate-suppressed content n-grams (2..4), the same filter every phrase hypothesis uses."""
    for toks in B.sentences(text):
        for n in range(lo, hi + 1):
            for i in range(0, len(toks) - n + 1):
                ng = " ".join(toks[i:i + n])
                if B.is_boilerplate_ngram(ng) or B.is_low_content(ng) or B.is_weak_label(ng):
                    continue
                yield ng


def _collect(ref: dict):
    """Single streamed pass over the needed monthly mirror files. Returns
    matched[case_id][party] = list of {off, low, nw, ds, inst} for each responding statement, where
    `low` is the lowercased title+text and `off` is days after the decision.

    LANE (docs/12 L1, docs/17 §3). This reads the raw mirror directly (not `iter_statements`), so it
    used to drop `date_source` — the field that says whether an event's window sits in one instrument
    or two. Each matched statement now carries `ds` (raw date_source) and `inst` (propublica|scraped).
    An event that straddles 2021-01-03 (e.g. a Jan-6-2021 study) can then isolate to one lane rather
    than compare the ProPublica import's tail against the scraper's start — the S4.7 sign inversion
    (-69.9% raw vs +75.5% lane-isolated) is what happens when it does not."""
    from . import provenance
    cases = ref["cases"]
    window = ref["_window_days"]
    by_month = defaultdict(dict)   # month -> {case_id: case}; DEDUPED (a case spans many days/2 months
    for c in cases:                # but must be counted ONCE per month, not once per in-window day). §verify-fix
        d0 = date.fromisoformat(c["date"])
        for k in range(0, window + 1):
            d = d0 + timedelta(days=k)
            by_month[f"{d.year:04d}-{d.month:02d}"][c["id"]] = c
    by_month = {m: list(cs.values()) for m, cs in by_month.items()}
    matched = {c["id"]: {"D": [], "R": []} for c in cases}
    word_re = re.compile(r"[a-z']+")
    for mkey in sorted(by_month):
        f = fetch.MIRROR / f"{mkey}.jsonl"
        if not f.exists():
            continue
        cand = by_month[mkey]
        for r in util.iter_jsonl(f):
            d = (r.get("date") or "")[:10]
            if len(d) != 10:
                continue
            m = r.get("member") or {}
            p = _PARTY.get(m.get("party"))
            if p not in ("D", "R"):
                continue
            try:
                dobj = date.fromisoformat(d)
            except Exception:
                continue
            src = provenance.date_source_of(r)
            inst = provenance.INSTRUMENTS.get(src) if src is not None else None
            low = None
            nw = None
            for c in cand:
                off = (dobj - date.fromisoformat(c["date"])).days
                if off < 0 or off > window:
                    continue
                if low is None:
                    low = ((r.get("title") or "") + " . " + (r.get("text") or "")).lower()
                    nw = len(word_re.findall(low))
                if any(a in low for a in c["anchors"]):
                    matched[c["id"]][p].append({"off": off, "low": low, "nw": nw, "ds": src, "inst": inst})
    return matched


def _valence(low: str, lex: dict):
    cel = any(t in low for t in lex["celebration"])
    con = any(t in low for t in lex["condemnation"])
    return cel, con


def run(topk=8, min_cell=10):
    ref = load_ref()
    lex = ref["_framing_lexicon"]
    cases = {c["id"]: c for c in ref["cases"]}
    matched = _collect(ref)

    series = []
    # aggregate accumulators
    half_signs = {"A": [], "B": []}          # sign(tone_gap) per qualifying case, D-more-negative=+1
    loser_louder = {"A": [0, 0], "B": [0, 0]}  # [times losing party more negative, qualifying cases]
    jaccards = {"A": [], "B": []}

    for cid, c in cases.items():
        half = c["half"]
        rec = {"id": c["id"], "name": c["name"], "date": c["date"], "half": half,
               "topic": c["topic"], "prevailing": c["prevailing"]}
        party_stats = {}
        top_sets = {}
        for p in ("D", "R"):
            rows = matched[cid][p]
            n = len(rows)
            first = min((x["off"] for x in rows), default=None)
            cel = con = 0
            phrases = Counter()
            for x in rows:
                pc, nc = _valence(x["low"], lex)
                cel += 1 if pc else 0
                con += 1 if nc else 0
                for ng in set(_content_ngrams(x["low"])):
                    phrases[ng] += 1
            top = phrases.most_common(topk)
            top_sets[p] = {ng for ng, _ in top}
            party_stats[p] = {
                "n": n, "first_day": first,
                "celebrate_rate": round(cel / n, 3) if n else None,
                "condemn_rate": round(con / n, 3) if n else None,
                "net_neg": round((con - cel) / n, 3) if n else None,
                "top_phrases": [[ng, ct] for ng, ct in top],
            }
        rec["D"], rec["R"] = party_stats["D"], party_stats["R"]
        # vocabulary divergence: 1 - Jaccard(topD, topR) among content phrases
        sd, sr = top_sets["D"], top_sets["R"]
        uni = len(sd | sr)
        jac = (len(sd & sr) / uni) if uni else None
        rec["phrase_overlap_jaccard"] = round(jac, 3) if jac is not None else None
        rec["shared_top_phrases"] = sorted(sd & sr)

        qualifies = party_stats["D"]["n"] >= min_cell and party_stats["R"]["n"] >= min_cell
        rec["qualifies_for_aggregate"] = qualifies
        if qualifies:
            tone_gap = party_stats["D"]["net_neg"] - party_stats["R"]["net_neg"]
            rec["tone_gap_D_minus_R"] = round(tone_gap, 3)
            sign = 1 if tone_gap > 0 else (-1 if tone_gap < 0 else 0)
            half_signs[half].append((c["id"], sign))
            if jac is not None:
                jaccards[half].append(jac)
            # loser-louder: the party whose position LOST is the non-prevailing party
            loser = "D" if c["prevailing"] == "R" else "R"
            winner = c["prevailing"]
            loser_louder[half][1] += 1
            if party_stats[loser]["net_neg"] > party_stats[winner]["net_neg"]:
                loser_louder[half][0] += 1
        series.append(rec)

    # aggregate PARTY-direction gate: dominant sign present in >=8 qualifying cases in BOTH halves,
    # AND the same dominant sign in both halves.
    def dominant(signs):
        pos = sum(1 for _i, s in signs if s > 0)
        neg = sum(1 for _i, s in signs if s < 0)
        if pos >= neg:
            return (1, pos, len(signs))
        return (-1, neg, len(signs))
    dom_a = dominant(half_signs["A"])
    dom_b = dominant(half_signs["B"])
    party_gate = (dom_a[1] >= 8 and dom_b[1] >= 8 and dom_a[0] == dom_b[0])

    # loser-louder (power/valence) structure across all qualifying cases
    ll_hits = loser_louder["A"][0] + loser_louder["B"][0]
    ll_tot = loser_louder["A"][1] + loser_louder["B"][1]

    from statistics import median
    med_jac_a = median(jaccards["A"]) if jaccards["A"] else None
    med_jac_b = median(jaccards["B"]) if jaccards["B"] else None

    powered = dom_a[2] >= 8 and dom_b[2] >= 8
    if not powered:
        verdict = "UNDERPOWERED"
    elif party_gate:
        verdict = "CONFIRMED"
    else:
        verdict = "DESCRIPTIVE"

    return {
        "id": "S4.1", "name": "One Court, Two Languages",
        "verdict": verdict,
        "n_cases": len(cases),
        "aggregate": {
            "party_direction_gate": party_gate,
            "half_A": {"qualifying": dom_a[2], "D_more_negative": sum(1 for _i, s in half_signs["A"] if s > 0),
                       "R_more_negative": sum(1 for _i, s in half_signs["A"] if s < 0),
                       "dominant_sign": dom_a[0], "dominant_count": dom_a[1]},
            "half_B": {"qualifying": dom_b[2], "D_more_negative": sum(1 for _i, s in half_signs["B"] if s > 0),
                       "R_more_negative": sum(1 for _i, s in half_signs["B"] if s < 0),
                       "dominant_sign": dom_b[0], "dominant_count": dom_b[1]},
            "loser_louder": {"A": loser_louder["A"], "B": loser_louder["B"], "all": [ll_hits, ll_tot]},
            "median_phrase_overlap_jaccard": {"A": med_jac_a and round(med_jac_a, 3),
                                              "B": med_jac_b and round(med_jac_b, 3)},
        },
        "series": series,
    }


if __name__ == "__main__":
    import sys
    out = run()
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
