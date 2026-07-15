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

# Amendment A1 windows
HALF_A_YEARS = set(range(2013, 2021))   # congresses 113-116
HALF_B_YEARS = set(range(2021, 2027))   # congresses 117-119
ALL_YEARS = sorted(HALF_A_YEARS | HALF_B_YEARS)


def _days(d1: str, d2: str) -> int:
    return (date.fromisoformat(d2) - date.fromisoformat(d1)).days


def _year(d: str) -> int:
    return int(d[:4])


def _half(year: int) -> str | None:
    return "A" if year in HALF_A_YEARS else ("B" if year in HALF_B_YEARS else None)


def _load_index():
    return list(H.iter_phrase_index())


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
def s1_1_ignition_width(rows, peak_min=15, cap=60, min_cell=8):
    """Ignition width = days(first_date -> peak_day), capped at `cap`, for phrases with peak>=peak_min.
    Median per ignition-year; CONFIRM = Spearman<0 (widths shrinking) in BOTH halves AND survives the
    density-matched control. Effect floor restated per A1: early-window median >= 1.5x late-window."""
    by_year = defaultdict(list)
    widths_by_year_records = defaultdict(list)  # for density control: keep the per-phrase widths
    for r in rows:
        if r["peak"] < peak_min or not r.get("peak_day"):
            continue
        y = _year(r["first_date"])
        if _half(y) is None:
            continue
        w = min(_days(r["first_date"], r["peak_day"]), cap)
        if w < 0:
            continue
        by_year[y].append(w)
        widths_by_year_records[y].append(w)

    series = [(y, median(by_year[y])) for y in sorted(by_year) if len(by_year[y]) >= min_cell]
    cells = {y: len(by_year[y]) for y in sorted(by_year)}
    a = [(y, m) for (y, m) in series if y in HALF_A_YEARS]
    b = [(y, m) for (y, m) in series if y in HALF_B_YEARS]
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
    return {"id": "S1.1", "name": "Industrialization of the Memo", "peak_min": peak_min,
            "artifact_guard": artifact,
            "series": series, "cells": cells, "dir_a": dir_a, "dir_b": dir_b,
            "early_median": early, "late_median": late, "ratio": ratio,
            "density_survives": density_survives, "verdict": verdict}


# --- S1.3 Phrase Lifespan Collapse ---------------------------------------------------------------
def s1_3_lifespan(rows, peak_min=10, min_cell=8):
    """Cross-era lifespan = days(global first_date -> global last_date) per phrase (peak>=peak_min,
    aggregated across congresses by ngram). Median per birth-year; CONFIRM = >=30% median drop A->B
    with both halves' internal trend agreeing (Spearman<0)."""
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
        if _half(y) is None:
            continue
        by_year[y].append(_days(a["first"], a["last"]))
    series = [(y, median(by_year[y])) for y in sorted(by_year) if len(by_year[y]) >= min_cell]
    cells = {y: len(by_year[y]) for y in sorted(by_year)}
    a_s = [(y, m) for (y, m) in series if y in HALF_A_YEARS]
    b_s = [(y, m) for (y, m) in series if y in HALF_B_YEARS]
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
    return {"id": "S1.3", "name": "Phrase Lifespan Collapse", "peak_min": peak_min,
            "artifact_guard": artifact,
            "series": series, "cells": cells, "dir_a": dir_a, "dir_b": dir_b,
            "early_median_lifespan": early, "late_median_lifespan": late, "median_drop": drop,
            "verdict": verdict, "note": "birth-year cohorts truncate near the window edge (right-censoring) — caveat on any card"}


# --- S1.2 Sync Ceiling (boundary-SAFE: single-day peaks, no span) --------------------------------
def s1_2_sync_ceiling(rows, active_by_year: dict):
    """Loudest single-day unison per year = max phrase peak whose peak_day falls in that year, divided
    by that year's active-member count (the coverage control — a bigger caucus can converge harder for
    free). CONFIRM = normalized ceiling rising in BOTH halves AND late >= 1.5x early."""
    ceil_raw = defaultdict(int)
    for r in rows:
        if not r.get("peak_day"):
            continue
        y = _year(r["peak_day"])
        if _half(y) is not None:
            ceil_raw[y] = max(ceil_raw[y], r["peak"])
    series, raw = [], {}
    for y in sorted(ceil_raw):
        am = active_by_year.get(str(y)) or active_by_year.get(y)
        raw[y] = ceil_raw[y]
        if am:
            series.append((y, ceil_raw[y] / am))
    a = [(y, v) for (y, v) in series if y in HALF_A_YEARS]
    b = [(y, v) for (y, v) in series if y in HALF_B_YEARS]
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
    return {"id": "S1.2", "name": "The Sync Ceiling", "series_norm": [(y, round(v, 4)) for y, v in series],
            "raw_ceiling": raw, "dir_a": dir_a, "dir_b": dir_b, "early_norm": early, "late_norm": late,
            "ratio": ratio, "verdict": verdict}


# --- S1.5 Weekend Memo (ignition weekday vs the all-statement baseline) ---------------------------
def s1_5_weekend_memo(rows, weekday_baseline: dict, peak_min=15):
    """Do coordinated ignitions (first_date of peak>=15 phrases) avoid weekends MORE than statements
    generally? Excess = ignition-weekday share / baseline-weekday share. CONFIRM = weekend excess < 1
    (under-represented) in BOTH halves, and the business-day fingerprint is real (weekday excess > 1)."""
    from collections import Counter
    base = Counter({int(k): v for k, v in weekday_baseline.items()})
    ig = {"A": Counter(), "B": Counter()}
    for r in rows:
        if r["peak"] < peak_min:
            continue
        y = _year(r["first_date"])
        h = _half(y)
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
    return {"id": "S1.5", "name": "The Weekend Memo", "peak_min": peak_min,
            "excess_A": {k: round(v, 2) if v is not None else None for k, v in ex_a.items()},
            "excess_B": {k: round(v, 2) if v is not None else None for k, v in ex_b.items()},
            "weekend_excess_A": weekend_a, "weekend_excess_B": weekend_b,
            "n_A": sum(ig["A"].values()), "n_B": sum(ig["B"].values()), "verdict": verdict}


# --- S1.7 The August Effect (recess proxy = the August district work period) ---------------------
def s1_7_august_effect(rows, monthly_stmts: dict, peak_min=15):
    """Does coordination collapse in recess, or is it pre-scheduled? Recess proxy = August (Congress is
    reliably in its district work period). Ignition rate = ignitions per 1k statements, August vs the
    rest of the year. CONFIRM (counterintuitive direction) = recess rate >= 70% of session rate in BOTH
    halves (coordination persists through recess); REFUTE if it craters. Coarse proxy, disclosed."""
    ig = {"A": {"aug": 0, "other": 0}, "B": {"aug": 0, "other": 0}}
    for r in rows:
        if r["peak"] < peak_min:
            continue
        y, mo = _year(r["first_date"]), int(r["first_date"][5:7])
        h = _half(y)
        if h is None:
            continue
        ig[h]["aug" if mo == 8 else "other"] += 1
    # statement denominators per period per half
    st = {"A": {"aug": 0, "other": 0}, "B": {"aug": 0, "other": 0}}
    for ym, c in monthly_stmts.items():
        y, mo = int(ym[:4]), int(ym[5:7])
        h = _half(y)
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
    return {"id": "S1.7", "name": "The August Effect", "peak_min": peak_min,
            "by_half": out, "recess_vs_session_ratio": {h: r and round(r, 2) for h, r in ratios.items()},
            "proxy": "August = recess", "verdict": verdict}


def monthly_statement_counts():
    """{YYYY-MM: count} over the statement-meta intermediate."""
    from collections import Counter
    c = Counter()
    for r in H.iter_stmt_meta():
        c[r["date"][:7]] += 1
    return dict(c)


def run(rows=None):
    rows = rows if rows is not None else _load_index()
    return [s1_1_ignition_width(rows), s1_3_lifespan(rows)]
