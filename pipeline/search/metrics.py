"""Metrics library for The Search — the correctness core (docs/12 §S0.3).

Every function is deterministic and stdlib-only. The coverage confound (§1.3) is the adversary these
are built against: raw counts grow with the corpus, so trend claims MUST ride rates and survive a
density-matched control. `split_halves` and `power_ok` encode the pre-registered CONFIRM gates.

Kill-fixtures (tests/test_search_metrics.py): each metric is proven to REFUSE a synthetic
pure-coverage-growth signal before it is trusted on real data (§1.12).
"""
from __future__ import annotations

import math
import random
from collections import Counter


# --- rates (never trend a raw count) -------------------------------------------------------------
def rate_per_1k(numerator: float, denominator: float) -> float | None:
    """Occurrences per 1,000 statements. None when the denominator is empty (an honest gap, never 0)."""
    if not denominator or denominator <= 0:
        return None
    return 1000.0 * numerator / denominator


def per_member_rate(numerator: float, active_members: int) -> float | None:
    if not active_members or active_members <= 0:
        return None
    return numerator / active_members


# --- rank correlation (stdlib Spearman, average-rank ties) ---------------------------------------
def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based average rank across the tie block
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float | None:
    """Spearman's rho. None if <3 usable pairs or either series is constant (rho undefined)."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    rx = _ranks([p[0] for p in pairs])
    ry = _ranks([p[1] for p in pairs])
    n = len(pairs)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    dx = math.sqrt(sum((r - mx) ** 2 for r in rx))
    dy = math.sqrt(sum((r - my) ** 2 for r in ry))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


# --- power floors (UNDERPOWERED is not REFUTED, §1.6) --------------------------------------------
def power_ok(n: int, floor: int) -> bool:
    return n is not None and n >= floor


# --- split-halves validation (§1.4): CONFIRM needs agreement in BOTH halves ----------------------
def split_direction(series_by_x: list[tuple[float, float]]) -> int | None:
    """Sign of the trend (Spearman of value vs ordering key) over a series of (x, value) points.
    Returns +1 / -1 / 0, or None if underpowered/constant. Used per half; CONFIRM requires the two
    halves to return the SAME non-zero sign."""
    if len(series_by_x) < 3:
        return None                    # too few points -> UNDERPOWERED, not a measured flat
    xs = [p[0] for p in series_by_x]
    ys = [p[1] for p in series_by_x]
    rho = spearman(xs, ys)
    if rho is None:
        return 0                       # >=3 points but values don't move -> measured FLAT (no trend)
    if rho > 0.10:
        return 1
    if rho < -0.10:
        return -1
    return 0


def confirms_in_both_halves(half_a: list[tuple[float, float]], half_b: list[tuple[float, float]],
                            expected_sign: int) -> bool:
    """The core CONFIRM gate: the expected trend direction must hold in BOTH pre-registered halves.
    A finding that only appears when the halves are pooled is exactly the split-leakage the program
    forbids. expected_sign is fixed at pre-registration (+1 rising, -1 falling)."""
    da = split_direction(half_a)
    db = split_direction(half_b)
    return da == expected_sign and db == expected_sign


# --- the coverage control (§1.3): density-matched subsample --------------------------------------
def density_matched_subsample(records: list, target_n: int, seed_key: str) -> list:
    """Refutation attempt #1 for every trend. A later, denser era mechanically produces narrower
    ignition widths / higher sync ceilings simply because more members are observed. To neutralize
    that, recompute the LATER era on a random subsample matched to the EARLIER era's daily/era volume.
    If the trend survives the subsample it is real; if it evaporates it is a coverage ARTIFACT.

    Deterministic: seeded by seed_key (no wall-clock/global RNG), so a rerun reproduces the sample."""
    if target_n >= len(records):
        return list(records)
    rng = random.Random(f"onscript-search::{seed_key}")
    idx = list(range(len(records)))
    rng.shuffle(idx)
    keep = sorted(idx[:target_n])
    return [records[i] for i in keep]


# --- symmetry (§1.5): both parties, always, and the power-position reframe ------------------------
def symmetry_table(value_by_party: dict[str, float]) -> dict:
    """Package a metric for publication with BOTH parties' numbers side by side and their gap. A
    non-trivial gap flags the power-position reframe check (does it attach to majority/minority /
    White-House control rather than party identity?) before any ⚠ neutrality review."""
    d = value_by_party.get("D")
    r = value_by_party.get("R")
    gap = (d - r) if (d is not None and r is not None) else None
    return {"D": d, "R": r, "gap": gap,
            "reframe_flag": gap is not None and abs(gap) > 0}


# --- difference-in-differences (§S0.3): deterministic arithmetic ----------------------------------
def did(treated_pre: float, treated_post: float, control_pre: float, control_post: float) -> float:
    """(treated_post - treated_pre) - (control_post - control_pre). The clean causal-design estimator
    for the event studies (e.g. lame-duck losers vs returning members over the same weeks)."""
    return (treated_post - treated_pre) - (control_post - control_pre)


# --- weekday skew (§S1.5) ------------------------------------------------------------------------
def weekday_excess(observed: Counter, baseline: Counter) -> dict[int, float]:
    """Observed-vs-baseline weekday distribution ratio (0=Mon..6=Sun). >1 = over-represented. Used to
    detect the business-day fingerprint of coordinated ignitions vs the all-statement baseline."""
    ob = sum(observed.values()) or 1
    bb = sum(baseline.values()) or 1
    out = {}
    for wd in range(7):
        o = observed.get(wd, 0) / ob
        b = baseline.get(wd, 0) / bb
        out[wd] = (o / b) if b > 0 else None
    return out
