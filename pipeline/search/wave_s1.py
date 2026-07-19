"""Wave S1 — pure-ledger hypotheses (docs/12 §S1). Reads the memoized phrase index; deterministic.

Analyzable window per amendment A1: congresses 113-119 (2013-2026). Split A = 2013-2020, B = 2021-2026.
Every hypothesis returns a full evidence dict (series + both-half directions + effect ratio + density
control + power) and a mechanical VERDICT. Numbers, not adjectives — the verdict follows the gate.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import median

from . import harness as H
from . import metrics as M

# Amendment A1 windows (the OLD seam-spanning split, retained for reference/graveyard only — NEVER
# used to bucket: A=2013-2020 is the ProPublica lane, B=2021-2026 is the scraper lane, so this split
# IS the provenance seam. Within-lane re-validation (docs/18 §5) uses the per-lane halves below.
HALF_A_YEARS = set(range(2013, 2021))   # congresses 113-116  (DO NOT bucket with this)
HALF_B_YEARS = set(range(2021, 2027))   # congresses 117-119  (DO NOT bucket with this)
ALL_YEARS = sorted(HALF_A_YEARS | HALF_B_YEARS)

# Within-lane halves (docs/17 §2, docs/18 §5). YEAR-keyed for the phrase/series/meta hypotheses;
# CONGRESS-keyed for the ones that split on congress (S1.11). Never mix the two forms in one hypothesis.
LANE_YEAR_HALVES = {
    "propublica": {"A": set(range(2013, 2017)), "B": set(range(2017, 2021))},   # 113-114 vs 115-116
    "scraped":    {"A": set(range(2021, 2024)), "B": set(range(2024, 2027))},   # 117 vs 118-119
}
LANE_CONGRESS_HALVES = {
    "propublica": {"A": {113, 114}, "B": {115, 116}},
    "scraped":    {"A": {117}, "B": {118, 119}},
}
LANE_CONGRESSES = {"propublica": range(113, 117), "scraped": range(117, 120)}


def year_halves_for(lane):
    return LANE_YEAR_HALVES[lane]


def congress_halves_for(lane):
    return LANE_CONGRESS_HALVES[lane]


def _days(d1: str, d2: str) -> int:
    return (date.fromisoformat(d2) - date.fromisoformat(d1)).days


def _year(d: str) -> int:
    return int(d[:4])


def _half(year: int, halves) -> str | None:
    """Which pre-registered half a year (or congress) falls in, or None. `halves` is REQUIRED — a
    default is exactly what let the seam-spanning split travel for 34 verdicts (docs/18 §5)."""
    return "A" if year in halves["A"] else ("B" if year in halves["B"] else None)


def _load_index(lane=None):
    return list(H.iter_phrase_index(lane=lane))


def _year_position_artifact(by_year: dict) -> bool:
    """Structural-confound guard (§4.4, amendment A2). The per-Congress shards seat each Congress in
    the ODD year, so any first_seen->span metric systematically differs between a Congress's year 1
    and year 2 (year 1 has a ~2-yr runway; year 2 has none). If odd-year and even-year medians diverge
    by >5x, the 'trend' is that boundary sawtooth, not a real signal -> ARTIFACT. Detects a KNOWN
    structural confound; it is not post-hoc tuning."""
    odd = [median(v) for y, v in by_year.items() if y % 2 == 1 and len(v) >= 8]
    even = [median(v) for y, v in by_year.items() if y % 2 == 0 and len(v) >= 8]
    if not odd or not even:
        return False
    mo, me = median(odd), median(even)
    hi, lo = max(mo, me), min(mo, me)
    return lo <= 0 or (hi / lo) > 5.0


# --- S1.1 Industrialization of the Memo ----------------------------------------------------------
def s1_1_ignition_width(rows, peak_min=15, cap=60, min_cell=8, *, lane=None, halves):
    """Ignition width = days(first_date -> peak_day), capped at `cap`, for phrases with peak>=peak_min.
    Median per ignition-year; CONFIRM = Spearman<0 (widths shrinking) in BOTH halves AND survives the
    density-matched control. Effect floor restated per A1: early-window median >= 1.5x late-window.
    Within-lane (docs/18 §5): `rows` are the lane's phrase index; `halves` are the lane's halves."""
    by_year = defaultdict(list)
    widths_by_year_records = defaultdict(list)  # for density control: keep the per-phrase widths
    for r in rows:
        if r["peak"] < peak_min or not r.get("peak_day"):
            continue
        y = _year(r["first_date"])
        if _half(y, halves) is None:
            continue
        w = min(_days(r["first_date"], r["peak_day"]), cap)
        if w < 0:
            continue
        by_year[y].append(w)
        widths_by_year_records[y].append(w)

    series = [(y, median(by_year[y])) for y in sorted(by_year) if len(by_year[y]) >= min_cell]
    cells = {y: len(by_year[y]) for y in sorted(by_year)}
    a = [(y, m) for (y, m) in series if y in halves["A"]]
    b = [(y, m) for (y, m) in series if y in halves["B"]]
    dir_a = M.split_direction(a)
    dir_b = M.split_direction(b)

    # effect ratio: earliest powered A-year median vs latest powered B-year median
    early = a[0][1] if a else None
    late = b[-1][1] if b else None
    ratio = (early / late) if (early and late) else None

    # density control: match each B-half year's phrase count to the min A-half cell, recompute median
    density_survives = None
    if a and b:
        min_a_cell = min(len(by_year[y]) for (y, _) in a)
        sub_series_b = []
        for (y, _) in b:
            sub = M.density_matched_subsample(widths_by_year_records[y], min_a_cell, f"s1.1:{y}")
            sub_series_b.append((y, median(sub)))
        # trend must persist in the subsampled B-half AND B stay below A
        density_survives = (M.split_direction(a + sub_series_b) == -1)

    powered = len(a) >= 2 and len(b) >= 2
    artifact = _year_position_artifact(by_year)
    if artifact:
        verdict = "ARTIFACT"        # congress-year-position sawtooth (A2) — metric ill-posed, deferred
    elif not powered:
        verdict = "UNDERPOWERED"
    elif dir_a == -1 and dir_b == -1 and ratio and ratio >= 1.5 and density_survives:
        verdict = "CONFIRMED"
    elif (dir_a == -1 and dir_b == -1) and not density_survives:
        verdict = "ARTIFACT"        # trend evaporates under the coverage control
    else:
        verdict = "REFUTED"
    return {"id": "S1.1", "name": "Industrialization of the Memo", "lane": lane, "peak_min": peak_min,
            "artifact_guard": artifact,
            "series": series, "cells": cells, "dir_a": dir_a, "dir_b": dir_b,
            "early_median": early, "late_median": late, "ratio": ratio,
            "density_survives": density_survives, "verdict": verdict}


# --- S1.3 Phrase Lifespan Collapse ---------------------------------------------------------------
def s1_3_lifespan(rows, peak_min=10, min_cell=8, *, lane=None, halves):
    """Cross-era lifespan = days(global first_date -> global last_date) per phrase (peak>=peak_min,
    aggregated across congresses by ngram). Median per birth-year; CONFIRM = >=30% median drop A->B
    with both halves' internal trend agreeing (Spearman<0). Within-lane (docs/18 §5): `rows` isolated
    to the lane; note the lifespan first->last cannot cross the lane edge because the lane's shards do
    not (propublica ends 2021-01-03)."""
    agg = {}
    for r in rows:
        if r["peak"] < peak_min:
            continue
        ng = r["ng"]
        a = agg.get(ng)
        if a is None:
            agg[ng] = {"first": r["first_date"], "last": r["last_date"], "peak": r["peak"]}
        else:
            a["first"] = min(a["first"], r["first_date"])
            a["last"] = max(a["last"], r["last_date"])
            a["peak"] = max(a["peak"], r["peak"])
    by_year = defaultdict(list)
    for ng, a in agg.items():
        y = _year(a["first"])
        if _half(y, halves) is None:
            continue
        by_year[y].append(_days(a["first"], a["last"]))
    series = [(y, median(by_year[y])) for y in sorted(by_year) if len(by_year[y]) >= min_cell]
    cells = {y: len(by_year[y]) for y in sorted(by_year)}
    a_s = [(y, m) for (y, m) in series if y in halves["A"]]
    b_s = [(y, m) for (y, m) in series if y in halves["B"]]
    dir_a, dir_b = M.split_direction(a_s), M.split_direction(b_s)
    early = median([m for (y, m) in a_s]) if a_s else None
    late = median([m for (y, m) in b_s]) if b_s else None
    drop = (1 - late / early) if (early and late and early > 0) else None
    powered = len(a_s) >= 2 and len(b_s) >= 2
    artifact = _year_position_artifact(by_year)
    if artifact:
        verdict = "ARTIFACT"        # same congress-boundary sawtooth + shard-edge right-censoring (A2)
    elif not powered:
        verdict = "UNDERPOWERED"
    elif dir_a == -1 and dir_b == -1 and drop is not None and drop >= 0.30:
        verdict = "CONFIRMED"
    else:
        verdict = "REFUTED"
    return {"id": "S1.3", "name": "Phrase Lifespan Collapse", "lane": lane, "peak_min": peak_min,
            "artifact_guard": artifact,
            "series": series, "cells": cells, "dir_a": dir_a, "dir_b": dir_b,
            "early_median_lifespan": early, "late_median_lifespan": late, "median_drop": drop,
            "verdict": verdict, "note": "birth-year cohorts truncate near the window edge (right-censoring) — caveat on any card"}


# --- S1.1' Industrialization of the Memo, REDEFINED (event-detection on the merged series) --------
def _bursts(series, gap=14):
    """Split a phrase's merged daily series into BURSTS = runs of active days no more than `gap` days
    apart. Each burst is a single rise-and-fall; its width (start->peak) is a real ignition speed,
    immune to the congress-boundary artifact (A2) because it's gap-defined, not congress- or
    calendar-bounded. A recurring phrase yields multiple bursts (it re-ignites)."""
    days = [(date.fromisoformat(d), c) for d, c in series if c > 0]
    if not days:
        return []
    out, cur = [], [days[0]]
    for prev, nxt in zip(days, days[1:]):
        if (nxt[0] - prev[0]).days <= gap:
            cur.append(nxt)
        else:
            out.append(cur); cur = [nxt]
    out.append(cur)
    return out


def s1_1_prime_ignition(series_rows, peak_min=15, gap=14, min_cell=8, *, lane=None, halves):
    """REDEFINED S1.1 (amendment A2). For every burst reaching peak>=peak_min, ignition width = days
    from the burst's first active day to its peak day. Median per burst-start year; CONFIRM =
    Spearman<0 in BOTH halves AND survives the density-matched control AND early >= 1.5x late.
    Within-lane (docs/18 §5): the lane's daily series never spans the seam, so a burst is a real
    within-instrument flare; a burst at the lane edge is naturally gap-terminated by the shard end."""
    by_year = defaultdict(list)
    for row in series_rows:
        for burst in _bursts(row["series"], gap):
            peak = max(c for _d, c in burst)
            if peak < peak_min:
                continue
            start = burst[0][0]
            peak_day = min(d for d, c in burst if c == peak)
            y = start.year
            if _half(y, halves) is not None:
                by_year[y].append((peak_day - start).days)
    series = [(y, median(by_year[y])) for y in sorted(by_year) if len(by_year[y]) >= min_cell]
    cells = {y: len(by_year[y]) for y in sorted(by_year)}
    a = [(y, m) for (y, m) in series if y in halves["A"]]
    b = [(y, m) for (y, m) in series if y in halves["B"]]
    dir_a, dir_b = M.split_direction(a), M.split_direction(b)
    early = a[0][1] if a else None
    late = b[-1][1] if b else None
    ratio = (early / late) if (early and late and late > 0) else None
    # density control: match later-half yearly burst counts to the min A-half cell, recompute
    density_survives = None
    if a and b:
        min_a = min(len(by_year[y]) for (y, _) in a)
        sub_b = [(y, median(M.density_matched_subsample(by_year[y], min_a, f"s1.1p:{y}"))) for (y, _) in b]
        density_survives = (M.split_direction(a + sub_b) == -1)
    artifact = _year_position_artifact(by_year)
    powered = len(a) >= 2 and len(b) >= 2
    if artifact:
        verdict = "ARTIFACT"        # if the boundary sawtooth somehow persists (it should not now)
    elif not powered:
        verdict = "UNDERPOWERED"
    elif dir_a == -1 and dir_b == -1 and ratio and ratio >= 1.5 and density_survives:
        verdict = "CONFIRMED"
    elif dir_a == -1 and dir_b == -1 and not density_survives:
        verdict = "ARTIFACT"
    else:
        verdict = "REFUTED"
    return {"id": "S1.1'", "name": "Industrialization of the Memo (redefined)", "lane": lane, "series": series,
            "cells": cells, "dir_a": dir_a, "dir_b": dir_b, "early_median": early, "late_median": late,
            "ratio": ratio and round(ratio, 2), "density_survives": density_survives,
            "artifact_guard": artifact, "verdict": verdict}


# --- S1.3' Phrase Lifespan, REDEFINED (burst duration on the merged series; censoring-safe) --------
def s1_3_prime_lifespan(series_rows, peak_min=15, gap=14, min_cell=8, cutoff="2026-07-09", censor_days=30,
                        *, lane=None, halves):
    """REDEFINED S1.3 (amendment A2). A 'talking point' = a burst (a flare reaching peak>=peak_min);
    its lifespan = the burst's duration (first->last active day). Bursts self-terminate at a >gap-day
    silence, so there is NO shard-edge censoring — except a burst still running near the data cutoff,
    which is DROPPED (censor_days). Median per burst-start year; CONFIRM = durations shrinking (dir<0)
    in BOTH halves AND >=30% drop early->late AND density-control survives (talking points burn out
    faster than they used to).

    LANE EDGE (docs/18 §5): the propublica lane ENDS at 2021-01-03, so its `cutoff` is the lane edge,
    not 2026-07-09 — a burst still alive at lane-end must be censored exactly as at the corpus cutoff,
    or its truncated duration reads as a (false) short lifespan. The driver passes the lane's cutoff."""
    from datetime import date as _d
    cut = _d.fromisoformat(cutoff)
    by_year = defaultdict(list)
    for row in series_rows:
        for burst in _bursts(row["series"], gap):
            if max(c for _dd, c in burst) < peak_min:
                continue
            first, last = burst[0][0], burst[-1][0]
            if (cut - last).days < censor_days:   # may still be active -> right-censored, drop
                continue
            if _half(first.year, halves) is not None:
                by_year[first.year].append((last - first).days)
    series = [(y, median(by_year[y])) for y in sorted(by_year) if len(by_year[y]) >= min_cell]
    cells = {y: len(by_year[y]) for y in sorted(by_year)}
    a = [(y, m) for (y, m) in series if y in halves["A"]]
    b = [(y, m) for (y, m) in series if y in halves["B"]]
    dir_a, dir_b = M.split_direction(a), M.split_direction(b)
    early = median([m for _y, m in a]) if a else None
    late = median([m for _y, m in b]) if b else None
    drop = (1 - late / early) if (early and late and early > 0) else None
    density_survives = None
    if a and b:
        min_a = min(len(by_year[y]) for (y, _) in a)
        sub_b = [(y, median(M.density_matched_subsample(by_year[y], min_a, f"s1.3p:{y}"))) for (y, _) in b]
        density_survives = (M.split_direction(a + sub_b) == -1)
    artifact = _year_position_artifact(by_year)
    powered = len(a) >= 2 and len(b) >= 2
    if artifact:
        verdict = "ARTIFACT"
    elif not powered:
        verdict = "UNDERPOWERED"
    elif dir_a == -1 and dir_b == -1 and drop is not None and drop >= 0.30 and density_survives:
        verdict = "CONFIRMED"
    elif dir_a == -1 and dir_b == -1 and not density_survives:
        verdict = "ARTIFACT"
    else:
        verdict = "REFUTED"
    return {"id": "S1.3'", "name": "Phrase Lifespan Collapse (redefined)", "lane": lane, "series": series,
            "cells": cells, "dir_a": dir_a, "dir_b": dir_b, "early_median_days": early,
            "late_median_days": late, "median_drop": drop and round(drop, 3),
            "density_survives": density_survives, "artifact_guard": artifact, "verdict": verdict}


# --- S1.2 Sync Ceiling (boundary-SAFE: single-day peaks, no span) --------------------------------
def s1_2_sync_ceiling(rows, active_by_year: dict, *, lane=None, halves):
    """Loudest single-day unison per year = max phrase peak whose peak_day falls in that year, divided
    by that year's active-member count (the coverage control — a bigger caucus can converge harder for
    free). CONFIRM = normalized ceiling rising in BOTH halves AND late >= 1.5x early. Within-lane
    (docs/18 §5): `active_by_year` is the LANE's active-member count (from the lane's stmt_meta)."""
    ceil_raw = defaultdict(int)
    for r in rows:
        if not r.get("peak_day"):
            continue
        y = _year(r["peak_day"])
        if _half(y, halves) is not None:
            ceil_raw[y] = max(ceil_raw[y], r["peak"])
    series, raw = [], {}
    for y in sorted(ceil_raw):
        am = active_by_year.get(str(y)) or active_by_year.get(y)
        raw[y] = ceil_raw[y]
        if am:
            series.append((y, ceil_raw[y] / am))
    a = [(y, v) for (y, v) in series if y in halves["A"]]
    b = [(y, v) for (y, v) in series if y in halves["B"]]
    dir_a, dir_b = M.split_direction(a), M.split_direction(b)
    early = a[0][1] if a else None
    late = b[-1][1] if b else None
    ratio = (late / early) if (early and late and early > 0) else None
    powered = len(a) >= 2 and len(b) >= 2
    if not powered:
        verdict = "UNDERPOWERED"
    elif dir_a == 1 and dir_b == 1 and ratio and ratio >= 1.5:
        verdict = "CONFIRMED"
    else:
        verdict = "REFUTED"
    return {"id": "S1.2", "name": "The Sync Ceiling", "lane": lane,
            "series_norm": [(y, round(v, 4)) for y, v in series],
            "raw_ceiling": raw, "dir_a": dir_a, "dir_b": dir_b, "early_norm": early, "late_norm": late,
            "ratio": ratio, "verdict": verdict}


# --- S1.5 Weekend Memo (ignition weekday vs the all-statement baseline) ---------------------------
def s1_5_weekend_memo(rows, weekday_baseline: dict, peak_min=15, *, lane=None, halves):
    """Do coordinated ignitions (first_date of peak>=15 phrases) avoid weekends MORE than statements
    generally? Excess = ignition-weekday share / baseline-weekday share. CONFIRM = weekend excess < 1
    (under-represented) in BOTH halves, and the business-day fingerprint is real (weekday excess > 1).
    Within-lane (docs/18 §4/§5): `weekday_baseline` is the LANE's weekday baseline — an era-pooled
    baseline normalizing a scraper-only half was the Session-16 triage bug this whole fix addresses."""
    from collections import Counter
    base = Counter({int(k): v for k, v in weekday_baseline.items()})
    ig = {"A": Counter(), "B": Counter()}
    for r in rows:
        if r["peak"] < peak_min:
            continue
        y = _year(r["first_date"])
        h = _half(y, halves)
        if h is None:
            continue
        try:
            wd = date.fromisoformat(r["first_date"]).weekday()
        except Exception:
            continue
        ig[h][wd] += 1
    ex_a = M.weekday_excess(ig["A"], base)
    ex_b = M.weekday_excess(ig["B"], base)
    weekend_a = [ex_a.get(5), ex_a.get(6)]
    weekend_b = [ex_b.get(5), ex_b.get(6)]
    both_avoid = all(v is not None and v < 1.0 for v in weekend_a + weekend_b)
    powered = sum(ig["A"].values()) >= 30 and sum(ig["B"].values()) >= 30
    verdict = ("UNDERPOWERED" if not powered else "CONFIRMED" if both_avoid else "REFUTED")
    return {"id": "S1.5", "name": "The Weekend Memo", "lane": lane, "peak_min": peak_min,
            "excess_A": {k: round(v, 2) if v is not None else None for k, v in ex_a.items()},
            "excess_B": {k: round(v, 2) if v is not None else None for k, v in ex_b.items()},
            "weekend_excess_A": weekend_a, "weekend_excess_B": weekend_b,
            "n_A": sum(ig["A"].values()), "n_B": sum(ig["B"].values()), "verdict": verdict}


# --- S1.7 The August Effect (recess proxy = the August district work period) ---------------------
def s1_7_august_effect(rows, monthly_stmts: dict, peak_min=15, *, lane=None, halves):
    """Does coordination collapse in recess, or is it pre-scheduled? Recess proxy = August (Congress is
    reliably in its district work period). Ignition rate = ignitions per 1k statements, August vs the
    rest of the year. CONFIRM (counterintuitive direction) = recess rate >= 70% of session rate in BOTH
    halves (coordination persists through recess); REFUTE if it craters. Coarse proxy, disclosed.
    Within-lane (docs/18 §5): `monthly_stmts` are the LANE's per-month statement denominators."""
    ig = {"A": {"aug": 0, "other": 0}, "B": {"aug": 0, "other": 0}}
    for r in rows:
        if r["peak"] < peak_min:
            continue
        y, mo = _year(r["first_date"]), int(r["first_date"][5:7])
        h = _half(y, halves)
        if h is None:
            continue
        ig[h]["aug" if mo == 8 else "other"] += 1
    # statement denominators per period per half
    st = {"A": {"aug": 0, "other": 0}, "B": {"aug": 0, "other": 0}}
    for ym, c in monthly_stmts.items():
        y, mo = int(ym[:4]), int(ym[5:7])
        h = _half(y, halves)
        if h is None:
            continue
        st[h]["aug" if mo == 8 else "other"] += c
    out = {}
    ratios = {}
    for h in ("A", "B"):
        aug_rate = M.rate_per_1k(ig[h]["aug"], st[h]["aug"])
        oth_rate = M.rate_per_1k(ig[h]["other"], st[h]["other"])
        out[h] = {"aug_rate": aug_rate and round(aug_rate, 3), "other_rate": oth_rate and round(oth_rate, 3),
                  "aug_ig": ig[h]["aug"], "aug_stmts": st[h]["aug"]}
        ratios[h] = (aug_rate / oth_rate) if (aug_rate and oth_rate) else None
    powered = all(st[h]["aug"] >= 200 for h in ("A", "B"))
    persists = all(ratios[h] is not None and ratios[h] >= 0.70 for h in ("A", "B"))
    if not powered:
        verdict = "UNDERPOWERED"
    elif persists:
        verdict = "CONFIRMED"
    else:
        verdict = "REFUTED"
    return {"id": "S1.7", "name": "The August Effect", "lane": lane, "peak_min": peak_min,
            "by_half": out, "recess_vs_session_ratio": {h: r and round(r, 2) for h, r in ratios.items()},
            "proxy": "August = recess", "verdict": verdict}


# --- S1.4-proper The Copy-Paste Caucus (statements-IN-groups share + density control) ------------
def _ingroup_share(statements):
    """Per party: (statements-in-a-near/joint-group share, total). joint_group != None = the statement
    is part of a same-day (near-)identical multi-member release (the copy-paste machinery)."""
    tot = {"D": 0, "R": 0}
    ing = {"D": 0, "R": 0}
    for s in statements:
        p = (s.get("member") or {}).get("party")
        if p in ("D", "R"):
            tot[p] += 1
            if s.get("joint_group"):
                ing[p] += 1
    return {p: {"share": (ing[p] / tot[p] if tot[p] else None), "n": tot[p], "in": ing[p]} for p in ("D", "R")}


def s1_4_verbatim(congresses=range(113, 120), *, lane=None, halves=None, min_cell=200):
    """The Copy-Paste Caucus — VERBATIM version (tractable + density-robust). A statement is 'copy-paste'
    if its same-day whitespace-normalized text is byte-identical to that of >=1 OTHER member that day (a
    verbatim co-signed / cloned release). Share per party per year. Unlike the fuzzy near-dup count
    (density-sensitive, killed the proxy), byte-identical grouping does NOT inflate with corpus size, so
    the share is inherently density-robust. CONFIRM = share rises in BOTH halves, both parties agreeing.
    (Near-identical/templated variants are excluded here for tractability — the verbatim floor.)

    LANE (docs/12 L1, docs/17 §4.3). The original REFUTED used A=2013-2020 / B=2021-2026 — the seam.
    That split is doubly dangerous here: verbatim co-signing is detected by same-DAY identical text, and
    the two lanes carry different rosters and different syndication behaviour, so a 'rise' across the
    seam could be one collector grouping more aggressively than the other. `lane` isolates it; the
    numerator and denominator are BOTH statement-counts within that lane (the ratio is a share, so the
    denominator-unit note in docs/17 §3 resolves to: same unit top and bottom, no cross-unit rise).
    The per-year power floor now applies WITHIN the lane."""
    import re
    if lane is not None:
        halves = halves or LANE_YEAR_HALVES[lane]
    day_text = defaultdict(lambda: defaultdict(set))   # date -> normtext -> {bioguide}
    rows = []
    for r in H.iter_statements(congresses=set(congresses), with_text=True, lane=lane):
        p, bio, txt = r.get("party"), r.get("bioguide"), (r.get("text") or "")
        if p not in ("D", "R") or not bio or not txt.strip():
            continue
        norm = re.sub(r"\s+", " ", txt).strip().lower()
        h = hash(norm)
        day_text[r["date"]][h].add(bio)
        rows.append((r["year"], p, r["date"], h))
    tot = defaultdict(lambda: {"D": 0, "R": 0})
    verb = defaultdict(lambda: {"D": 0, "R": 0})
    for year, p, d, h in rows:
        tot[year][p] += 1
        if len(day_text[d][h]) >= 2:      # same text, >=2 distinct members that day = verbatim group
            verb[year][p] += 1
    ha = halves["A"] if halves else HALF_A_YEARS
    hb = halves["B"] if halves else HALF_B_YEARS
    in_window = {y for y in tot if int(y) in ha or int(y) in hb}
    share = {y: {p: (verb[y][p] / tot[y][p] if tot[y][p] else None) for p in ("D", "R")} for y in sorted(in_window)}
    dirs = {}
    for p in ("D", "R"):
        a = [(int(y), share[y][p]) for y in share if int(y) in ha and share[y][p] is not None]
        b = [(int(y), share[y][p]) for y in share if int(y) in hb and share[y][p] is not None]
        dirs[f"{p}_A"], dirs[f"{p}_B"] = M.split_direction(a), M.split_direction(b)
    rises = all(dirs[f"{p}_{h}"] == 1 for p in ("D", "R") for h in ("A", "B"))
    powered = all(tot[y]["D"] >= min_cell and tot[y]["R"] >= min_cell for y in in_window)
    verdict = "UNDERPOWERED" if not powered else ("CONFIRMED" if rises else "REFUTED")
    return {"id": "S1.4", "name": "The Copy-Paste Caucus (verbatim)", "lane": lane,
            "share_by_year": {y: {p: round(v, 4) if v is not None else None for p, v in d.items()}
                              for y, d in share.items()},
            "directions": dirs, "verdict": verdict}


def s1_4_proper(congresses=range(113, 120), seed="s1.4", *, lane=None, chalves=None):
    """The Copy-Paste Caucus done right: SHARE of statements that are part of a near/joint-identical
    group (not the density-sensitive group COUNT the proxy used), per party per Congress. DENSITY
    CONTROL (§1.3): re-normalize each Congress's RAW records subsampled to the sparsest Congress's
    volume — if the rising share survives, it's real; if it flattens, the detector just found more
    near-dups in a denser corpus. CONFIRM = share rises in BOTH halves AND survives the control, both
    parties agreeing in direction.

    LANE (docs/12 L1, docs/18 §5). `lane` gives `load_congress_records` the same lane filter, so the
    density control runs WITHIN one instrument — the whole point, because a joint pair split across
    lanes cannot near-dup-collapse within a lane, and the collapse rate is exactly what this measures.
    `chalves` are the lane's CONGRESS halves; `congresses` must be the lane's congresses."""
    from .. import normalize
    from ..alexandria import load_congress_records
    chalves = chalves or (LANE_CONGRESS_HALVES[lane] if lane else {"A": set(range(113, 117)), "B": set(range(117, 120))})
    full, recs_by_c = {}, {}
    for c in congresses:
        recs = load_congress_records(c, lane=lane)
        recs_by_c[c] = recs
        st = normalize.normalize_records(recs, run_id=f"s1.4-{c}" + (f"-{lane}" if lane else ""))
        full[c] = _ingroup_share(st)
    # density control: subsample each Congress's raw records to the sparsest Congress's total, re-normalize
    totals = {c: full[c]["D"]["n"] + full[c]["R"]["n"] for c in congresses}
    target = min(totals.values())
    matched = {}
    for c in congresses:
        recs = recs_by_c[c]
        n_target = min(len(recs), int(target * len(recs) / max(totals[c], 1)))
        sub = M.density_matched_subsample(recs, n_target, f"{seed}:{c}")
        st = normalize.normalize_records(sub, run_id=f"s1.4m-{c}" + (f"-{lane}" if lane else ""))
        matched[c] = _ingroup_share(st)

    def half_series(data, party):
        return ([(c, data[c][party]["share"]) for c in congresses if c in chalves["A"] and data[c][party]["share"] is not None],
                [(c, data[c][party]["share"]) for c in congresses if c in chalves["B"] and data[c][party]["share"] is not None])

    out = {"lane": lane,
           "full": {c: {p: round(full[c][p]["share"], 4) if full[c][p]["share"] is not None else None
                        for p in ("D", "R")} for c in congresses},
           "matched": {c: {p: round(matched[c][p]["share"], 4) if matched[c][p]["share"] is not None else None
                           for p in ("D", "R")} for c in congresses},
           "target_volume": target}
    dirs = {}
    for label, data in (("full", full), ("matched", matched)):
        for p in ("D", "R"):
            a, b = half_series(data, p)
            dirs[f"{label}_{p}_A"] = M.split_direction([(c, s) for c, s in a])
            dirs[f"{label}_{p}_B"] = M.split_direction([(c, s) for c, s in b])
    out["directions"] = dirs
    # POWER (docs/18 §5): the both-halves gate is a split_direction over CONGRESS-share points, which
    # needs >=3 congresses per half. No single lane has that — propublica A/B are {113,114}/{115,116}
    # (2 each), scraped A/B are {117}/{118,119} (1 and 2). So within a lane the congress-split gate is
    # UNMEETABLE and every direction comes back None; reporting that as REFUTED would be a false
    # negative (cf. S3.6 — a T1 power requirement no in-lane data can satisfy). The year-keyed verbatim
    # floor (s1_4_verbatim, Session 18) is the runnable within-lane form of this hypothesis.
    powered = all(len([c for c in congresses if c in chalves[h]]) >= 3 for h in ("A", "B"))
    rises_full = all(dirs.get(f"full_{p}_{h}") == 1 for p in ("D", "R") for h in ("A", "B"))
    survives = all(dirs.get(f"matched_{p}_{h}") == 1 for p in ("D", "R") for h in ("A", "B"))
    if not powered:
        verdict = "UNDERPOWERED"   # congress-split gate needs >=3 congresses/half; no lane has it
    elif rises_full and survives:
        verdict = "CONFIRMED"
    elif rises_full and not survives:
        verdict = "ARTIFACT"       # rose at full volume, evaporated under the density control
    else:
        verdict = "REFUTED"
    out.update({"id": "S1.4", "name": "The Copy-Paste Caucus", "lane_congress_split_powered": powered,
                "verdict": verdict})
    return out


# --- S1.10 Bipartisanship Has a Season (does bipartisan signaling flee before elections?) --------
_BIPARTISAN = ("bipartisan", "across the aisle", "both sides of the aisle", "reach across the aisle",
               "my republican colleague", "my democratic colleague", "republican and democratic colleague")


def s1_10_bipartisan_season(elections, congresses=range(113, 120), window=90, lane=None):
    """Deterministic bipartisan-signal rate ('bipartisan', 'across the aisle', ...) in the `window` days
    BEFORE each general election vs the `window` days AFTER. Hypothesis: collegiality 'flies south' ~90
    days out and returns after. MANDATORY PLACEBO CONTROL (§4.5): the same before/after comparison on a
    fake Nov-4 in ODD (non-election) years — if that ALSO troughs, the pattern is SEASONAL (recess/
    campaign fall vs winter legislating), not electoral, and the verdict is ARTIFACT, not CONFIRMED.
    Both computed in one pass. Symmetric (parties pooled — a calendar effect).

    SEAM (docs/12 L1, docs/17 §4.3). Each cycle is a before/after comparison across an anchor date, so
    a cycle whose ±window straddles 2021-01-03 compares the ProPublica lane (its BEFORE) against the
    scraper lane (its AFTER) — the difference-in-instruments dressed as a difference-in-season. The
    real 2020 cycle (window 2020-08-06..2021-02-02) is exactly that, and so is the 2021 placebo. Any
    cycle whose window spans the seam is DROPPED (assert_no_seam_span, applied per cycle rather than
    raised, because dropping the one bad cycle is the fix — not aborting the whole comparison). With
    `lane` set, statements are additionally isolated to that lane so a surviving cycle is single-lane
    end to end."""
    from datetime import date, timedelta
    from . import provenance
    real_all = [date.fromisoformat(v) for v in elections.values()]
    placebo_all = [date(y, 11, 4) for y in range(2013, 2027, 2)]   # odd non-election years, same window

    def straddles(anchor):
        span = [(anchor - timedelta(days=window)).isoformat(), (anchor + timedelta(days=window)).isoformat()]
        return provenance.spans_seam(span)
    real_dates = [d for d in real_all if not straddles(d)]
    placebo_dates = [d for d in placebo_all if not straddles(d)]
    dropped = {"real": [d.year for d in real_all if straddles(d)],
               "placebo": [d.year for d in placebo_all if straddles(d)]}

    def blank():
        return defaultdict(lambda: [0, 0])
    pre, post = {"real": blank(), "plac": blank()}, {"real": blank(), "plac": blank()}
    for r in H.iter_statements(congresses=set(congresses), with_text=True, lane=lane):
        try:
            d = date.fromisoformat(r["date"])
        except Exception:
            continue
        bip = 1 if any(p in (r.get("text") or "").lower() for p in _BIPARTISAN) else 0
        for kind, dates in (("real", real_dates), ("plac", placebo_dates)):
            for e in dates:
                delta = (e - d).days
                if 0 < delta <= window:
                    pre[kind][e.year][0] += bip; pre[kind][e.year][1] += 1
                elif -window <= delta < 0:
                    post[kind][e.year][0] += bip; post[kind][e.year][1] += 1

    def cycles_of(kind):
        out = {}
        for y in sorted(set(pre[kind]) | set(post[kind])):
            pr = (pre[kind][y][0] / pre[kind][y][1]) if pre[kind][y][1] else None
            po = (post[kind][y][0] / post[kind][y][1]) if post[kind][y][1] else None
            out[y] = {"pre_rate": pr and round(pr, 4), "post_rate": po and round(po, 4),
                      "pre_n": pre[kind][y][1], "post_n": post[kind][y][1],
                      "trough": (pr is not None and po is not None and pr < po)}
        return out
    real_c, plac_c = cycles_of("real"), cycles_of("plac")

    def trough_frac(cyc):
        t = [c for c in cyc.values() if c["pre_rate"] is not None and c["post_rate"] is not None]
        return (sum(1 for c in t if c["trough"]), len(t))
    rt, rn = trough_frac(real_c)
    pt, pn = trough_frac(plac_c)
    real_troughs = rn >= 4 and rt > rn / 2
    placebo_troughs = pn >= 4 and pt > pn / 2
    if placebo_troughs:
        verdict = "ARTIFACT"        # seasonal, not electoral — the placebo shows the same trough
    elif real_troughs:
        verdict = "CONFIRMED"
    else:
        verdict = "REFUTED"
    return {"id": "S1.10", "name": "Bipartisanship Has a Season", "lane": lane,
            "cycles": real_c, "placebo": plac_c, "dropped_seam_cycles": dropped,
            "real_troughs": f"{rt}/{rn}", "placebo_troughs": f"{pt}/{pn}",
            "confound": "seasonal (placebo also troughs)" if placebo_troughs else None, "verdict": verdict}


# --- S1.6 The 90-Day Snap (does message discipline tighten before elections?) --------------------
def s1_6_ninety_day_snap(disc_index, elections, window=90, prior=270, *, lane=None, halves):
    """For each general election, weighted discipline (sum on_message / sum statements) in the 90 days
    BEFORE election vs the prior 90-day window (E-270..E-90), per party. A 'snap' = pre-election
    discipline exceeds the prior window. CONFIRM = snap in a MAJORITY of cycles in BOTH halves, both
    parties (message discipline measurably tightens for the campaign). Within-lane (docs/18 §5):
    `disc_index` is the LANE's discipline. Both S1.6 windows are PRE-election, so unlike S1.10 the 2020
    cycle stays entirely propublica (its windows are Feb-Nov 2020) — no seam straddle here."""
    def window_index(party, e_iso, lo, hi):
        s = m = 0
        for day, rec in disc_index.get(party, {}).items():
            delta = (date.fromisoformat(e_iso) - date.fromisoformat(day)).days
            if lo < delta <= hi:      # `delta` days BEFORE the election
                s += rec["s"]; m += rec["m"]
        return (m / s) if s else None
    cycles = {}
    for yr, e_iso in sorted(elections.items()):
        y = int(yr)
        h = _half(y, halves)
        if h is None:
            continue
        row = {}
        for p in ("D", "R"):
            pre = window_index(p, e_iso, 0, window)
            base = window_index(p, e_iso, window, prior)
            row[p] = {"pre90": pre and round(pre, 3), "prior": base and round(base, 3),
                      "snap": (pre is not None and base is not None and pre > base)}
        cycles[yr] = {"half": h, **row}
    # tally snaps per half per party
    tally = {("A", "D"): [0, 0], ("A", "R"): [0, 0], ("B", "D"): [0, 0], ("B", "R"): [0, 0]}
    for yr, c in cycles.items():
        for p in ("D", "R"):
            key = (c["half"], p)
            if c[p]["pre90"] is not None and c[p]["prior"] is not None:
                tally[key][1] += 1
                if c[p]["snap"]:
                    tally[key][0] += 1
    # majority in both halves, both parties
    powered = all(tally[k][1] >= 2 for k in tally)
    majorities = all(tally[k][0] > tally[k][1] / 2 for k in tally if tally[k][1] > 0)
    verdict = "UNDERPOWERED" if not powered else ("CONFIRMED" if majorities else "REFUTED")
    return {"id": "S1.6", "name": "The 90-Day Snap", "lane": lane, "cycles": cycles,
            "snap_tally": {f"{h}-{p}": f"{tally[(h,p)][0]}/{tally[(h,p)][1]}" for (h, p) in tally},
            "verdict": verdict}


# --- S1.8 The SOTU Gravity Well (the annual cross-party unison peak + its decay) ------------------
def s1_8_sotu(by_day, window=21, norm_by=None, *, lane=None, halves):
    """Each year's PEAK cross-party unison day is the SOTU day (no hardcoded dates). Report its
    magnitude + the shared-reality HALF-LIFE = days after the peak until daily unison first falls below
    half the peak. CONFIRM (pre-registered) = half-life declining in BOTH halves AND >=40% total drop.
    Also reports the peak-magnitude trend (is the biggest shared-language day shrinking?). Within-lane
    (docs/18 §5): `by_day` is the LANE's cross-party unison series."""
    from datetime import date, timedelta
    years = defaultdict(dict)
    for d, c in by_day.items():
        years[int(d[:4])][d] = c
    peak_mag, half_life, peak_days = {}, {}, {}
    for y, days in years.items():
        if _half(y, halves) is None or not days:
            continue
        pday = max(days, key=lambda d: days[d])
        pm = days[pday]
        peak_days[y] = pday
        peak_mag[y] = pm
        pd = date.fromisoformat(pday)
        hl = window
        for delta in range(1, window + 1):
            if days.get((pd + timedelta(days=delta)).isoformat(), 0) < pm / 2:
                hl = delta
                break
        half_life[y] = hl
    hl_a = [(y, half_life[y]) for y in sorted(half_life) if y in halves["A"]]
    hl_b = [(y, half_life[y]) for y in sorted(half_life) if y in halves["B"]]
    pm_a = [(y, peak_mag[y]) for y in sorted(peak_mag) if y in halves["A"]]
    pm_b = [(y, peak_mag[y]) for y in sorted(peak_mag) if y in halves["B"]]
    hl_dir_a, hl_dir_b = M.split_direction(hl_a), M.split_direction(hl_b)
    from statistics import median
    hl_early = median([h for _y, h in hl_a]) if hl_a else None
    hl_late = median([h for _y, h in hl_b]) if hl_b else None
    hl_drop = (1 - hl_late / hl_early) if (hl_early and hl_late and hl_early > 0) else None
    powered = len(hl_a) >= 2 and len(hl_b) >= 2
    if not powered:
        verdict = "UNDERPOWERED"
    elif hl_dir_a == -1 and hl_dir_b == -1 and hl_drop is not None and hl_drop >= 0.40:
        verdict = "CONFIRMED"
    else:
        verdict = "REFUTED"
    return {"id": "S1.8", "name": "The SOTU Gravity Well", "lane": lane,
            "peak_day_by_year": peak_days, "peak_magnitude": dict(sorted(peak_mag.items())),
            "half_life_days": dict(sorted(half_life.items())),
            "hl_dir_a": hl_dir_a, "hl_dir_b": hl_dir_b, "hl_early": hl_early, "hl_late": hl_late,
            "hl_drop": hl_drop and round(hl_drop, 3),
            "peak_mag_dir_a": M.split_direction(pm_a), "peak_mag_dir_b": M.split_direction(pm_b),
            "verdict": verdict}


# --- S1.9 The 2022 Self-Audit (replicate the founder's finding on the symmetric corpus) ----------
def _fivegrams(text: str, strip_idx=None) -> set:
    """Distinctive content 5-grams (hashed to ints for fast set ops), boilerplate excluded. A shared
    5-gram is strong evidence of phrase reuse; the smaller sets make the pairwise overlap tractable.

    docs/19 §4 rider: when strip_idx (a nomenclature name index, nomenclature.load_index(congress)) is
    given, drop every 5-gram whose token window overlaps an official-name span, so a shared 5-gram
    measures MESSAGE reuse rather than two offices independently naming the same bill or committee."""
    from .. import boilerplate
    out = set()
    for toks in boilerplate.sentences(text):
        runs = None
        if strip_idx is not None:
            from .. import nomenclature
            runs = nomenclature.name_spans(toks, strip_idx)
        for i in range(0, len(toks) - 4):
            if runs and any(not (i + 4 < r0 or i > r1) for r0, r1, _c in runs):
                continue   # overlaps an official-name span -> nomenclature, not an independent message
            ng = " ".join(toks[i:i + 5])
            if not boilerplate.is_boilerplate_ngram(ng):
                out.add(hash(ng))
    return out


def s1_9_self_audit(congresses=(117,), min_members_week=6, cap=40, seed="s1.9", exclude_joint=True,
                    lane=None, strip_nomenclature=False):
    """Replicate the 2022 predecessor's finding (Democrats coordinate tighter) on PRESS RELEASES.
    Metric: mean pairwise weekly content-5-gram Jaccard overlap per party, with MATCHED member counts
    (subsample the larger party to the smaller each week — the pre-registered control so a party's
    higher overlap isn't just more members). ADVERSARIAL CONTROL (§4.5): exclude_joint drops verbatim
    co-signed releases (identical text under >=2 members in a week) so the overlap measures INDEPENDENT
    coordination, not co-signing — press releases (unlike the 2022 tweets) contain joint statements.
    Pre-committed: EITHER outcome publishes (replication or reversal). Deterministic (seeded).

    LANE (docs/12 L1, docs/17 §4.2): the window is congress 117 (2021-22), which the brief calls
    "lane-clean by construction". It is 99.6% clean, not 100%: 144 ProPublica-import records dated
    exactly 2021-01-03 (the 117th's first day, the import's LAST day) fall in 117. `lane='scraped'`
    excludes them so the whole window is one instrument. The measured effect of the exclusion is
    nil — the CONFIRMED verdict holds identically — but the re-affirmation is only honest if it is
    actually run within one lane rather than asserted to be."""
    import random
    from itertools import combinations
    # docs/19 §4 rider: strip official-name spans from the 5-grams, so a shared 5-gram is message reuse,
    # not two offices independently naming the same bill/committee. Index is cumulative 108..max(congress).
    strip_idx = None
    if strip_nomenclature:
        from .. import nomenclature
        strip_idx = nomenclature.load_index(max(congresses))
    # collect per-statement so joint (cross-member verbatim) releases can be identified + excluded
    stmts = []  # (party, week, bio, texthash, grams)
    for r in H.iter_statements(congresses=set(congresses), with_text=True, lane=lane):
        p, bio = r.get("party"), r.get("bioguide")
        if p not in ("D", "R") or not bio:
            continue
        try:
            iy, iw, _ = date.fromisoformat(r["date"]).isocalendar()
        except Exception:
            continue
        text = r.get("text") or ""
        grams = _fivegrams(text, strip_idx=strip_idx)
        if grams:
            stmts.append((p, (iy, iw), bio, hash(text.strip()), grams))
    # a texthash appearing under >=2 distinct bioguides in the same week = a joint/co-signed release
    wk_text_bios = defaultdict(set)
    for p, wk, bio, th, _g in stmts:
        wk_text_bios[(wk, th)].add(bio)
    joint = {k for k, bios in wk_text_bios.items() if len(bios) >= 2}
    joint_dropped = {"D": 0, "R": 0}
    by = {"D": defaultdict(lambda: defaultdict(set)), "R": defaultdict(lambda: defaultdict(set))}
    for p, wk, bio, th, grams in stmts:
        if exclude_joint and (wk, th) in joint:
            joint_dropped[p] += 1
            continue
        by[p][wk][bio] |= grams

    def mean_pairwise(sets):
        tot = cnt = 0.0
        for a, b in combinations(sets, 2):
            u = len(a | b)
            if u:
                tot += len(a & b) / u
                cnt += 1
        return (tot / cnt) if cnt else None

    weekly = {"D": [], "R": []}
    weeks = sorted(set(by["D"]) | set(by["R"]))
    for wk in weeks:
        md = {b: g for b, g in by["D"].get(wk, {}).items() if g}
        mr = {b: g for b, g in by["R"].get(wk, {}).items() if g}
        n = min(len(md), len(mr))
        if n < min_members_week:
            continue
        n = min(n, cap)
        rng = random.Random(f"{seed}:{wk}")
        sd = [md[b] for b in sorted(md)]; rng.shuffle(sd)
        se = [mr[b] for b in sorted(mr)]; random.Random(f"{seed}:{wk}:r").shuffle(se)
        jd, jr = mean_pairwise(sd[:n]), mean_pairwise(se[:n])
        if jd is not None and jr is not None:
            weekly["D"].append(jd); weekly["R"].append(jr)

    from statistics import mean
    nD, nR = len(weekly["D"]), len(weekly["R"])
    mD = mean(weekly["D"]) if weekly["D"] else None
    mR = mean(weekly["R"]) if weekly["R"] else None
    # per-week paired sign test: in how many matched weeks does D exceed R?
    d_gt_r = sum(1 for a, b in zip(weekly["D"], weekly["R"]) if a > b)
    powered = nD >= 20 and nR >= 20
    if not powered:
        verdict = "UNDERPOWERED"
    elif mD is not None and mR is not None:
        # this is a REPLICATION test: it always resolves to a finding (both outcomes publish)
        verdict = "CONFIRMED" if (mD > mR and d_gt_r > nD * 0.6) else "REFUTED"
    else:
        verdict = "UNDERPOWERED"
    return {"id": "S1.9", "name": "The 2022 Self-Audit", "congresses": list(congresses),
            "exclude_joint": exclude_joint, "joint_releases_dropped": joint_dropped,
            "mean_weekly_overlap_D": mD and round(mD, 5), "mean_weekly_overlap_R": mR and round(mR, 5),
            "weeks_matched": nD, "weeks_D_exceeds_R": d_gt_r,
            "direction": ("D>R (replicates)" if (mD and mR and mD > mR) else "R>=D (reverses)"),
            "verdict": verdict,
            "note": "REPLICATION — 'CONFIRMED' means the 2022 finding replicates (D tighter); 'REFUTED' means it reverses. Both publish."}


# --- S1.11 Delegation Echo (same-state members share phrases beyond chance) ----------------------
def _same_state_pairs(members, state_of):
    """Same-state pairs among a phrase's members = sum_s C(count_s, 2). O(M)."""
    from collections import Counter
    c = Counter(state_of[m] for m in members if m in state_of)
    return sum(n * (n - 1) // 2 for n in c.values()), sum(c.values())


def s1_11_delegation_echo(member_rows, state_of, k_perm=50, seed="s1.11", *, lane=None, chalves):
    """Do same-state delegations share phrases beyond chance? Observed same-state co-use pairs vs a
    permutation null that SHUFFLES the state labels across members (preserving each state's delegation
    size — so California's size can't fake the effect). ratio = observed / mean(null). CONFIRM =
    ratio >= 1.5 in BOTH halves. Deterministic (seeded permutations). Within-lane (docs/18 §5):
    `member_rows` are the lane's member index; `chalves` are the lane's CONGRESS halves (this
    hypothesis splits on congress, not year) — propublica {113,114}/{115,116}, scraped {117}/{118,119}."""
    import random
    halves = {"A": [], "B": []}
    for r in member_rows:
        h = _half(r["congress"], chalves)
        if h is None:
            continue
        ms = [m for m in r["members"] if m in state_of]
        if len(ms) >= 2:
            halves[h].append(ms)
    all_members = sorted({m for rows in halves.values() for ms in rows for m in ms})
    result = {}
    for h, phrases in halves.items():
        if not phrases:
            result[h] = None
            continue
        obs = tot = 0
        for ms in phrases:
            sp, tp = _same_state_pairs(ms, state_of)
            obs += sp
            tot += len(ms) * (len(ms) - 1) // 2
        # null: permute the state assignment across the member population, recompute
        real_states = [state_of[m] for m in all_members]
        nulls = []
        for k in range(k_perm):
            rng = random.Random(f"{seed}:{h}:{k}")
            perm = real_states[:]
            rng.shuffle(perm)
            pmap = dict(zip(all_members, perm))
            nobs = sum(_same_state_pairs(ms, pmap)[0] for ms in phrases)
            nulls.append(nobs)
        mean_null = sum(nulls) / len(nulls)
        ratio = (obs / mean_null) if mean_null else None
        result[h] = {"phrases": len(phrases), "observed_pairs": obs, "total_pairs": tot,
                     "mean_null_pairs": round(mean_null, 1), "ratio": ratio and round(ratio, 2),
                     "same_state_rate": round(obs / tot, 4) if tot else None}
    ra = result.get("A", {}) and result["A"]["ratio"] if result.get("A") else None
    rb = result.get("B", {}) and result["B"]["ratio"] if result.get("B") else None
    powered = result.get("A") and result.get("B") and result["A"]["phrases"] >= 30 and result["B"]["phrases"] >= 30
    if not powered:
        verdict = "UNDERPOWERED"
    elif ra and rb and ra >= 1.5 and rb >= 1.5:
        verdict = "CONFIRMED"
    else:
        verdict = "REFUTED"
    return {"id": "S1.11", "name": "Delegation Echo", "lane": lane, "by_half": result,
            "ratio_A": ra, "ratio_B": rb, "verdict": verdict}


def monthly_statement_counts(lane=None):
    """{YYYY-MM: count} over the statement-meta intermediate (lane-isolated when lane is set)."""
    from collections import Counter
    c = Counter()
    for r in H.iter_stmt_meta(lane=lane):
        c[r["date"][:7]] += 1
    return dict(c)


def run(lane, rows=None):
    """Thin driver for the two phrase-index hypotheses WITHIN one lane. The full within-lane
    re-validation of all eleven S1 items lives in scripts/search/revalidate_s1_shards.py (docs/18 §5)."""
    rows = rows if rows is not None else _load_index(lane=lane)
    h = year_halves_for(lane)
    return [s1_1_ignition_width(rows, lane=lane, halves=h), s1_3_lifespan(rows, lane=lane, halves=h)]
