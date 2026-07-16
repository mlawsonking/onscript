"""Kill-fixtures for the day-readiness gate (§deploy-hardening 2026-07-16).

This gate can HOLD publication, so a wrong threshold breaks the streak. Every trap is pinned here
BEFORE it is wired into the live daily path:
  * a normal WEEKEND must never be held (the same-weekday baseline is the whole point),
  * a genuinely late/thin day must be held (not published thin),
  * a late day that later fills must be RECOVERED (never skipped -> no hole in the series),
  * a day that never fills must be force-finalized (never livelock the streak).
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import readiness as R  # noqa: E402

# a realistic congressional corpus: weekdays ~200, weekends ~20
_END = date(2026, 7, 15)


def _corpus(weeks=8, weekday=200, weekend=20, overrides=None):
    counts = {}
    for k in range(weeks * 7, 0, -1):
        d = _END - timedelta(days=k)
        counts[d.isoformat()] = weekend if d.weekday() >= 5 else weekday
    counts.update(overrides or {})
    return counts


def _never_final(_day):
    return False


def test_a_normal_weekend_is_READY_not_held():
    """THE TRAP: a Saturday with a perfectly normal Saturday volume (20) is only 10% of the ALL-DAYS
    median (~200). Judged against an all-days baseline it would be held forever and the streak would
    die every weekend. The same-weekday baseline must call it READY."""
    counts = _corpus()
    sat = next((_END - timedelta(days=k)).isoformat() for k in range(1, 8)
               if (_END - timedelta(days=k)).weekday() == 5)
    counts[sat] = 20                      # a completely normal Saturday
    r = R.day_readiness(counts, sat)
    assert r["ready"] is True, r
    assert r["baseline"] == 20            # judged against Saturdays, not Tuesdays


def test_a_thin_late_day_is_HELD():
    """Upstream still landing: a weekday with a fraction of its same-weekday median is NOT ready."""
    counts = _corpus()
    wd = next((_END - timedelta(days=k)).isoformat() for k in range(1, 8)
              if (_END - timedelta(days=k)).weekday() < 5)
    counts[wd] = 12                       # ~6% of the 200 weekday median -> upstream is late
    r = R.day_readiness(counts, wd)
    assert r["ready"] is False and r["share"] < R.READY_RATIO
    assert "upstream likely still landing" in r["reason"]


def test_no_history_never_blocks():
    """Absence of a baseline is not evidence of incompleteness — never block a new corpus/era."""
    r = R.day_readiness({"2026-07-15": 3}, "2026-07-15")
    assert r["ready"] is True and r["baseline"] == 0.0


def test_hold_then_RECOVER_the_late_day_never_skip_it():
    """The whole point: a late day is HELD (run no-ops, $0), then RECOVERED by a later run once the
    data lands — never marched past and lost."""
    pd = _END.isoformat()
    caught_up = lambda d: d != pd                  # the backlog is final; only the product day is pending
    thin = _corpus(overrides={pd: 10})             # product day arrives thin -> hold
    out = R.select_target_day(thin, caught_up, pd)
    assert out["day"] is None and "HOLD" in out["reason"]      # no-op: no cluster/distill/API spend

    filled = _corpus(overrides={pd: 210})          # upstream lands -> the SAME day is now selected
    out2 = R.select_target_day(filled, caught_up, pd)
    assert out2["day"] == pd and out2["forced"] is False


def test_a_day_that_never_fills_is_force_finalized_not_livelocked():
    """Wait for it, but never forever: past MAX_WAIT_DAYS publish what we have (degraded) so a quiet
    holiday can't wedge the pipeline and stop every later day from ever publishing."""
    pd = _END.isoformat()
    stale_day = (_END - timedelta(days=R.MAX_WAIT_DAYS)).isoformat()
    pending = {stale_day, pd}                       # everything older is already final
    counts = _corpus(overrides={stale_day: 5, pd: 210})
    out = R.select_target_day(counts, lambda d: d not in pending, pd)
    assert out["day"] == stale_day and out["forced"] is True
    assert "never leave a hole" in out["reason"]


def test_oldest_first_so_the_series_fills_chronologically():
    counts = _corpus(overrides={(_END - timedelta(days=1)).isoformat(): 205, _END.isoformat(): 210})
    finals = set()
    out = R.select_target_day(counts, lambda d: d in finals, _END.isoformat())
    assert out["day"] == (_END - timedelta(days=R.LOOKBACK_DAYS)).isoformat()  # oldest unfinalized first


def test_a_ZERO_data_day_is_never_force_published_as_nothing_today():
    """THE 'nothing today' GUARD (caught by a dry-run against real state before shipping): a day with
    ZERO statements is a dataless gap, not a late day. Force-publishing it would print an empty
    "nothing today" page — exactly what we must never do. It is skipped past (stays un-final, costless
    to re-check, self-heals if data ever lands) and the run proceeds to a day that has something."""
    pd = _END.isoformat()
    dead = (_END - timedelta(days=R.MAX_WAIT_DAYS)).isoformat()
    pending = {dead, pd}
    counts = _corpus(overrides={dead: 0, pd: 210})     # `dead` has NOTHING; pd is fine
    out = R.select_target_day(counts, lambda d: d not in pending, pd)
    assert out["day"] == pd and out["forced"] is False   # skipped the empty day, published the real one
    # ...but a day that is merely THIN (real data, just few) IS force-published rather than lost
    counts2 = _corpus(overrides={dead: 9, pd: 210})
    out2 = R.select_target_day(counts2, lambda d: d not in pending, pd)
    assert out2["day"] == dead and out2["forced"] is True and "on 9 statements" in out2["reason"]


def test_all_final_is_a_noop():
    counts = _corpus(overrides={_END.isoformat(): 210})
    out = R.select_target_day(counts, lambda _d: True, _END.isoformat())
    assert out["day"] is None and "all days in the lookback are final" in out["reason"]
