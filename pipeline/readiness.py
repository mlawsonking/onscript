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

FOUR TRAPS ENCODED HERE (each would break the streak if gotten wrong):
  1. **Same-weekday baseline.** Congress publishes far less on weekends. Gating against an all-days
     trailing median would mark every Saturday "not ready" and hold publication forever. The baseline
     is the trailing SAME-WEEKDAY median.
  2. **No-history means ready.** With no baseline (new corpus/era) we must not block; absence of
     evidence is not evidence of incompleteness.
  3. **Regime shifts (S70).** A six-week same-weekday window straddles the session/recess boundary,
     so a normal deep-recess Tuesday reads as a half-landed session Tuesday and is held. Congress
     leaving town is not upstream being late. The baseline therefore takes the LOWER of a long and a
     recent same-weekday median: the recent arm tracks a level change within two weeks, the long arm
     stops one loud week from raising the bar.
  4. **Baselines too small to carry a ratio (S70).** Weekend baselines run 5 to 11 statements, where
     one statement moves the share by five to ten points and the ratio measures noise. Below
     `MIN_JUDGEABLE_BASELINE` the comparison is WITHHELD rather than answered: readiness does not
     block, the volume alert does not page, and both say so in words.

THE OWNER (docs/37 rule 1). `expected_volume` is the single definition of "what should this day
hold". The publication gate reads it here and the volume alert reads it through `ops.volume_anomaly`,
so the two can never judge the same day against two different baselines. That seam is exactly how
2026-08-09, a regime-normal recess Sunday, cleared this gate and then paged the operator anyway.
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta

READY_RATIO = 0.40        # ready when the day has >= this share of its expected volume
BASELINE_WEEKS = 6        # long arm: how many prior same-weekdays form the stable baseline
RECENT_WEEKS = 3          # short arm: how many prior same-weekdays track the current regime
MIN_JUDGEABLE_BASELINE = 20   # below this a ratio measures noise, so the comparison is withheld
MIN_BASELINE_DAYS = 2     # a median over one observation is that observation, not a norm
LOOKBACK_DAYS = 5         # how far back a run will reach to recover a late day
MAX_WAIT_DAYS = 2         # after this, publish what we have (degraded) rather than livelock the streak
MIN_PUBLISHABLE = 1       # a day with ZERO statements is never force-published — see below


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _same_weekday(counts_by_day: dict, day: str, weeks: int) -> tuple[float, int]:
    """(median, n) over the prior `weeks` same weekdays that are present in the corpus."""
    d0 = _d(day)
    prior = []
    for k in range(1, weeks + 1):
        prev = (d0 - timedelta(days=7 * k)).isoformat()
        if prev in counts_by_day:
            prior.append(counts_by_day[prev])
    return (float(statistics.median(prior)) if prior else 0.0), len(prior)


def same_weekday_baseline(counts_by_day: dict, day: str, weeks: int = BASELINE_WEEKS) -> float:
    """Median volume of the trailing `weeks` SAME weekdays before `day` (0.0 if no history).
    Same-weekday, because a Saturday must be judged against Saturdays, never against a Tuesday."""
    return _same_weekday(counts_by_day, day, weeks)[0]


def expected_volume(counts_by_day: dict, day: str, *, weeks: int = BASELINE_WEEKS,
                    recent_weeks: int = RECENT_WEEKS) -> dict:
    """How many statements this day should hold. THE baseline; both arms read this one function.

    Returns {baseline, long_baseline, recent_baseline, judgeable, method}. `baseline` is the lower
    of the two same-weekday medians, which is what makes it regime-robust in the direction that
    costs the streak:

      * a level DROP (Congress goes into recess) is tracked by the recent arm within two weeks,
        so a normal recess day is not read as a half-landed session day;
      * a single loud week (2026-07-22 ran 380 against a 232 norm) cannot raise the bar, because
        the long arm caps it.

    Taking the lower value can only loosen the gate, so it cannot hide a day that never landed: a
    day that never landed reads 1 or 2 statements against either arm. The residual is the other
    direction, a level RISE (Congress returns), where the recent arm lags for two weeks and the
    gate is more permissive than it needs to be. That costs a thin day published rather than a
    real day held, and `MAX_WAIT_DAYS` would have published it two days later regardless.
    """
    long_, n_long = _same_weekday(counts_by_day, day, weeks)
    recent, n_recent = _same_weekday(counts_by_day, day, recent_weeks)
    if n_long < MIN_BASELINE_DAYS:
        # One observation is not a norm. At the start of a corpus or an era a single busy Saturday
        # would otherwise set a judgeable bar for the Saturday after it.
        return {"baseline": long_, "long_baseline": long_, "recent_baseline": recent,
                "observations": n_long, "recent_observations": n_recent, "judgeable": False,
                "method": ("no same-weekday history" if not n_long else
                           f"only {n_long} same-weekday observation, under the "
                           f"{MIN_BASELINE_DAYS} a median needs")}
    # The recent arm needs its window FULL before it may lower the bar. A median over three
    # observations survives one odd week; a median over one IS that week, and a single quiet
    # same-weekday would then set the bar for the next seven days.
    if n_recent == recent_weeks and recent < long_:
        baseline, method = recent, f"recent {recent_weeks}-week same-weekday median"
    else:
        baseline, method = long_, f"trailing {weeks}-week same-weekday median"
    return {"baseline": baseline, "long_baseline": long_, "recent_baseline": recent,
            "observations": n_long, "recent_observations": n_recent,
            "judgeable": baseline >= MIN_JUDGEABLE_BASELINE, "method": method}


def day_readiness(counts_by_day: dict, day: str, ratio: float = READY_RATIO) -> dict:
    """Is this day's data actually IN the mirror yet?

    {ready, count, baseline, share, judgeable, baseline_method, reason}. An unjudgeable day (no
    same-weekday history, or a baseline too small to carry a ratio) is READY: absence of a usable
    baseline is not evidence of incompleteness. Publishability is a separate question and is
    answered by `select_target_day`, which never publishes a day holding nothing.
    """
    count = counts_by_day.get(day, 0)
    exp = expected_volume(counts_by_day, day)
    baseline, judgeable = exp["baseline"], exp["judgeable"]
    row = {"count": count, "baseline": baseline, "judgeable": judgeable,
           "baseline_method": exp["method"]}
    if not judgeable:
        why = (exp["method"] if baseline <= 0 or exp["method"].startswith("only") else
               f"same-weekday baseline {baseline:g} is under the {MIN_JUDGEABLE_BASELINE} needed "
               f"to carry a ratio")
        return {"ready": True, "share": None, **row,
                "reason": f"{why}, cannot judge, do not block"}
    share = count / baseline
    ready = share >= ratio
    return {"ready": ready, "share": round(share, 3), **row,
            "reason": ("ready" if ready else f"only {count} vs {exp['method']} {baseline:g} "
                       f"({share:.0%} < {ratio:.0%}), upstream likely still landing")}


def resolve_focus_day(days_present, product_day: str, *, explicit: str | None = None) -> dict:
    """Which day does RUN A measure and write? The cursor, and the one rule it must obey.

    THE HOLE THIS CLOSES (S73, the 2026-09-08 orphan). RUN A used to take the newest day present
    in the corpus: `focus_day = days_present[-1]` in `deterministic.run`. The congress-press mirror
    pushes every morning around 09:30Z, so by the evening collect a handful of statements dated the
    RUN's OWN day have usually landed. The cursor followed them, and that had two consequences,
    both of which reached production:

      * A SAME-DAY FOCUS. The run measured a day that was still hours from being over, and every
        surface keyed to it was built from a fraction of it. On 2026-09-09 the whole instrument
        keyed to a day holding ONE statement, and `phrases/top.json` went to zero rows.
      * A SKIPPED DAY. The cursor was a maximum with no memory of what it had already written, so
        yesterday was vaulted over the moment a same-day statement appeared. Between 2026-07-12 and
        2026-09-09 it skipped thirteen days. Of the nine that fell after the silence board was wired
        on 2026-07-29, ALL NINE are missing their board: 2026-08-03, 08-05, 08-13, 08-16, 08-21,
        08-26, 08-31, 09-06 and 09-08. 2026-09-08, Congress's first day back from recess, lost its
        day record as well, and no later run would ever have written it.

    THE RULE. The focus day is never later than the product day, which is by definition the last
    New York calendar day that is actually over. A corpus ending BEFORE the product day still
    governs, so a backfill or a stalled mirror focuses the newest day it holds. This clamps the
    future and never the past.

    Skipping is prevented separately, by the sweep over `sweep_window`: clamping alone would still
    leave a hole on any day a run does not happen. The two together are the invariant that matters,
    which is that no judgeable day passes through the window unwritten.

    `explicit` is the operator's `--focus-day`. It is honored, because a repair knows which day it
    means, but a day past the product day is REPORTED: nothing downstream can compute an honest age
    for a day that has not happened.

    Pure. The clock arrives as `product_day`, never sampled here (docs/37 rule 5). ISO dates compare
    correctly as strings, which is why this needs no date parsing.

    Returns {day, requested, clamped, future, reason}.
    """
    newest = max(days_present) if days_present else None
    if explicit:
        future = explicit > product_day
        return {"day": explicit, "requested": explicit, "clamped": False, "future": future,
                "reason": ("explicit --focus-day override" if not future else
                           f"explicit --focus-day {explicit} is past the product day {product_day}; "
                           f"honored as an override, but its age is not meaningful")}
    if newest is None:
        return {"day": product_day, "requested": None, "clamped": False, "future": False,
                "reason": "no statements in the corpus, so the product day stands in"}
    if newest > product_day:
        return {"day": product_day, "requested": newest, "clamped": True, "future": False,
                "reason": (f"the corpus already holds {newest}, a day that is not over yet; "
                           f"measuring the product day {product_day} instead")}
    return {"day": newest, "requested": newest, "clamped": False, "future": False,
            "reason": ("the newest day in the corpus is the product day" if newest == product_day
                       else f"the corpus ends at {newest}, behind the product day {product_day}")}


def sweep_window(focus_day: str, *, lookback: int = LOOKBACK_DAYS) -> list[str]:
    """Every day RUN A is responsible for keeping written this run, oldest first.

    Same width and same direction as `select_target_day`'s walk, deliberately: the stage that
    WRITES a day and the stage that PUBLISHES it must reach exactly as far back as each other. A
    write window narrower than the publication window would hand assemble a day whose deterministic
    half nobody built; a wider one would rebuild days that are long since final.

    Bounded by `LOOKBACK_DAYS`, so the cost of the sweep is a constant, not a function of how long
    the corpus is. A hole older than the window is out of reach by design and is an operator repair,
    not a daily cost.
    """
    d0 = _d(focus_day)
    return [(d0 - timedelta(days=k)).isoformat() for k in range(lookback, -1, -1)]


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
        # MIN_PUBLISHABLE guards BOTH routes to publication, not just the forced one (S70). An
        # unjudgeable day is ready by design, so without this guard a dataless Saturday would take
        # the ready route and print an empty "nothing today" page rather than self-healing.
        if r["ready"] and r["count"] >= MIN_PUBLISHABLE:
            return {"day": day, "forced": False, "readiness": r, "reason": "ready"}
        # not ready — but has it waited too long? Publish what we have rather than livelock.
        #
        # AGE IS COUNTED IN PRODUCT DAYS, NOT CALENDAR DAYS, and the difference is one full day.
        # `p0` is already the PRIOR New York day, so a day is "0 days old" on the first run after
        # it ends, and `MAX_WAIT_DAYS` of 2 force-finalizes it on the third calendar day after it.
        # Worked from the incident that made this worth writing down (S73): 2026-09-07 was held on
        # the 09-08 runs (age 0) and the 09-09 runs (age 1, the "only 1d old" in the 09-09 23:28Z
        # log), and force-finalized on 09-10 (age 2). That is three calendar days of lag on a day
        # upstream never filled, and it is the intended reading of MAX_WAIT_DAYS rather than an
        # arithmetic slip: the unit is the pipeline's own product day throughout, so this number
        # and `ops.collection_maturity`'s `age_days` always agree. Changing the lag means changing
        # MAX_WAIT_DAYS, which is a threshold and therefore not an implementation decision.
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
