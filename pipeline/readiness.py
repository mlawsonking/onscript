"""Day readiness + target selection — the "wait, don't skip" gate (§deploy-hardening 2026-07-16).

THE HOLE THIS CLOSES. The daily path ran once at a fixed cron, always targeting `product_day()` (the
prior NY day). If the congress-press mirror was LATE at that moment we ingested a partial day,
published it thin, and then the next run advanced `product_day` — so the late day was **skipped
permanently**, punching a hole in the time-series (the one asset the project calls the moat). The
old `_volume_anomaly` noticed thin days but only ALERTED; it never held.

THE RULE. A run assembles the OLDEST not-yet-final day in the lookback window that is READY. If none
is ready it NO-OPS ($0 — no cluster, no distill, no API call) and a later retry picks it up. A day
that never becomes ready is force-finalized after `MAX_WAIT_DAYS` so a genuinely quiet day (holiday,
recess weekend) can never livelock the streak — wait for it, but never forever.

TWO TRAPS ENCODED HERE (both would break the streak if gotten wrong):
  1. **Same-weekday baseline.** Congress publishes far less on weekends. Gating against an all-days
     trailing median would mark every Saturday "not ready" and hold publication forever. The baseline
     is the trailing SAME-WEEKDAY median.
  2. **No-history means ready.** With no baseline (new corpus/era) we must not block; absence of
     evidence is not evidence of incompleteness.
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta

READY_RATIO = 0.55        # ready when the day has >= this share of its trailing same-weekday median
BASELINE_WEEKS = 6        # how many prior same-weekdays form the baseline
LOOKBACK_DAYS = 5         # how far back a run will reach to recover a late day
MAX_WAIT_DAYS = 2         # after this, publish what we have (degraded) rather than livelock the streak
MIN_PUBLISHABLE = 1       # a day with ZERO statements is never force-published — see below


def _d(s: str) -> date:
    return date.fromisoformat(s)


def same_weekday_baseline(counts_by_day: dict, day: str, weeks: int = BASELINE_WEEKS) -> float:
    """Median volume of the trailing `weeks` SAME weekdays before `day` (0.0 if no history).
    Same-weekday, because a Saturday must be judged against Saturdays — never against a Tuesday."""
    d0 = _d(day)
    prior = []
    for k in range(1, weeks + 1):
        prev = (d0 - timedelta(days=7 * k)).isoformat()
        if prev in counts_by_day:
            prior.append(counts_by_day[prev])
    return float(statistics.median(prior)) if prior else 0.0


def day_readiness(counts_by_day: dict, day: str, ratio: float = READY_RATIO) -> dict:
    """Is this day's data actually IN the mirror yet? {ready, count, baseline, share, reason}."""
    count = counts_by_day.get(day, 0)
    baseline = same_weekday_baseline(counts_by_day, day)
    if baseline <= 0:
        return {"ready": True, "count": count, "baseline": 0.0, "share": None,
                "reason": "no same-weekday history — cannot judge, do not block"}
    share = count / baseline
    ready = share >= ratio
    return {"ready": ready, "count": count, "baseline": baseline, "share": round(share, 3),
            "reason": ("ready" if ready else f"only {count} vs same-weekday median {baseline:g} "
                       f"({share:.0%} < {ratio:.0%}) — upstream likely still landing")}


def select_target_day(counts_by_day: dict, is_final, product_day: str, *,
                      lookback: int = LOOKBACK_DAYS, max_wait: int = MAX_WAIT_DAYS,
                      ratio: float = READY_RATIO) -> dict:
    """Pick the day this run should assemble. Oldest-first over the lookback window so a late day is
    RECOVERED rather than skipped; chronological, so the series never gets a hole.

    `is_final(day) -> bool` reports whether that day was already finalized (never re-assemble it).
    Returns {day|None, forced, readiness, reason}. day=None => this run should NO-OP ($0).
    """
    p0 = _d(product_day)
    for k in range(lookback, -1, -1):                 # oldest -> newest
        day = (p0 - timedelta(days=k)).isoformat()
        if is_final(day):
            continue
        r = day_readiness(counts_by_day, day, ratio=ratio)
        if r["ready"]:
            return {"day": day, "forced": False, "readiness": r, "reason": "ready"}
        # not ready — but has it waited too long? Publish what we have rather than livelock.
        age = (p0 - _d(day)).days
        if age >= max_wait:
            if r["count"] < MIN_PUBLISHABLE:
                # ZERO data, not a late day. Force-publishing here would print "nothing today" for a day
                # that simply has no statements (a dataless gap, or state we do not hold). Never do that:
                # skip past it. It stays un-final and costless to re-check, so if data EVER lands it is
                # picked up on a later run — self-healing, no marker, no empty page. §deploy-hardening.
                continue
            return {"day": day, "forced": True, "readiness": r,
                    "reason": f"waited {age}d and upstream never filled — finalizing degraded on "
                              f"{r['count']} statements, never leave a hole in the series"}
        return {"day": None, "forced": False, "readiness": r,
                "reason": f"{day} not ready ({r['reason']}) and only {age}d old — HOLD, retry later"}
    return {"day": None, "forced": False, "readiness": None,
            "reason": "nothing to do — all days in the lookback are final"}
