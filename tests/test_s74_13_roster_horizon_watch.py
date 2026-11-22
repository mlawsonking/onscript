"""S74-13 Package 3: the roster horizon is visible before it arrives.

Past the committed roster's horizon every page prints bare counts (S74-11, F1). The watchdog, which
already pages the operator through ntfy, now carries the horizon and the days left on every tick and
alarms at 14 days or fewer, so the January step (the 120th Congress) is seen coming. Built on the
committed roster, not a fixture, so a refresh that moves the horizon moves these expectations with it.
"""
from __future__ import annotations

import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pipeline import denominators, watchdog


def _shift(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def test_the_committed_roster_is_quiet_well_inside_its_horizon_and_says_so():
    horizon = denominators.roster_horizon()
    product_day = _shift(horizon, -(watchdog.ROSTER_HORIZON_WARN_DAYS + 1))
    [finding] = watchdog.check_roster_horizon(product_day)
    assert finding["level"] == "ok", finding
    assert finding["evidence"]["roster_horizon"] == horizon
    assert finding["evidence"]["days_left"] == watchdog.ROSTER_HORIZON_WARN_DAYS + 1
    assert horizon in finding["detail"]


def test_fourteen_days_or_fewer_alarms_and_past_the_horizon_keeps_alarming():
    horizon = denominators.roster_horizon()
    for offset in (watchdog.ROSTER_HORIZON_WARN_DAYS, 1, 0):
        [finding] = watchdog.check_roster_horizon(_shift(horizon, -offset))
        assert finding["level"] == "alarm", (offset, finding)
        assert finding["evidence"]["days_left"] == offset
        assert "P13" in finding["detail"]
    [past] = watchdog.check_roster_horizon(_shift(horizon, 2))
    assert past["level"] == "alarm" and past["evidence"]["days_left"] == -2
    assert "bare counts" in past["detail"]


def test_a_roster_that_speaks_for_no_day_alarms_rather_than_reporting_health():
    [finding] = watchdog.check_roster_horizon("2026-11-21", roster_table={})
    assert finding["level"] == "alarm"


def test_the_full_probe_carries_the_finding_into_the_alarms_it_pages():
    horizon = denominators.roster_horizon()
    with tempfile.TemporaryDirectory() as td:
        now = datetime.fromisoformat(horizon).replace(tzinfo=timezone.utc)
        result = watchdog.evaluate(derived=Path(td), now=now, product_day=_shift(horizon, -3))
    checks = {f["check"]: f for f in result["findings"]}
    assert checks["roster_horizon"]["level"] == "alarm"
    assert any(f["check"] == "roster_horizon" for f in result["alarms"])
    assert "roster_horizon" in watchdog._report(result)
