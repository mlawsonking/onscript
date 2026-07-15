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


def run(rows=None):
    rows = rows if rows is not None else _load_index()
    return [s1_1_ignition_width(rows), s1_3_lifespan(rows)]
