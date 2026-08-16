"""S70 acceptance: one regime-aware baseline, read by the publication gate and the volume alert.

TWO ARMS OF ONE DISEASE. Baselines built on session-regime volumes misjudge recess-regime days.

  Arm 1, the publication gate. The 2026-08-13 12:11Z assemble held 2026-08-11 because the day
  carried "only 96 vs same-weekday median 215 (45% < 55%)". 96 is a normal deep-recess Tuesday.
  The trailing six same-weekdays reached back through the 07-28 and 08-04 recess-adjacent Tuesdays
  into 07-21, 07-14, 07-07 and 06-30, which were session Tuesdays running 220 to 250. Upstream was
  healthy at the time: the 2026-08-13 collect manifest records source_freshness ok, age 4.26 hours,
  corpus through 08-12. Congress leaving town is not upstream being late.

  Arm 2, the volume alert. On 2026-08-10 the operator was paged "low volume on 2026-08-09: 6
  (median 141.5)" for a normal recess Sunday. S65's maturity arm read a same-weekday baseline, so
  6 statements cleared the Sunday bar and the day was judged mature; the anomaly arm then measured
  those 6 against an all-days trailing median of 141.5. Both pages the alert produced after S65
  landed were weekends measured against weekdays.

THE FIXTURES BELOW ARE THE REAL SERIES. Counts come from the committed day records, which are the
counts the days actually assembled from, used as production-shaped input and never asserted equal
to a fresh live build (docs/37 rules 2 and 3). The two days that never assembled leave no day
record, so their readings are frozen literals quoted from the committed collect manifests.
"""
from __future__ import annotations

import ast
import inspect
import json
from datetime import date, timedelta
from pathlib import Path

from pipeline import config, ops, readiness, run_collect

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"

# Frozen readings for the two held days, from the committed manifests. A later re-collect must not
# be able to erase the incident (the S65 pattern).
HELD_TUESDAY = "2026-08-11"
HELD_TUESDAY_AT_D1 = 89          # collect-2026-08-12.json, volume.today
HELD_TUESDAY_AT_D2 = 96          # the 2026-08-13 12:11Z assemble reading, quoted in the S70 order
HELD_TUESDAY_OLD_BASELINE = 215.0    # the same-weekday median both runs recorded
HELD_WEDNESDAY = "2026-08-12"
HELD_WEDNESDAY_AT_D1 = 86        # collect-2026-08-13.json, volume.today

RECESS_SUNDAY = "2026-08-09"     # 6 statements; the false page of 2026-08-10
RECESS_SATURDAY = "2026-08-08"   # 32 statements; the false page of 2026-08-09
SESSION_WEDNESDAY = "2026-07-22"  # 377 statements against a 232 norm, the loudest day in the series


def _committed_day_counts() -> dict[str, int]:
    """Statements per day from the committed day records, D plus R."""
    counts = {}
    for path in sorted((DERIVED / "days").glob("*.json")):
        day = json.loads(path.read_text(encoding="utf-8"))
        total = 0
        for line in (day.get("daily_lines") or {}).values():
            statements = ((line or {}).get("stats") or {}).get("statements")
            if isinstance(statements, int):
                total += statements
        if total:
            counts[day["day"]] = total
    return counts


def _corpus(counts: dict[str, int]) -> list[dict]:
    return [{"published_at": day, "lane": 1} for day, n in counts.items() for _ in range(n)]


def _august() -> dict[str, int]:
    """The committed series plus the two days that were held and so never wrote a day record."""
    return {**_committed_day_counts(),
            HELD_TUESDAY: HELD_TUESDAY_AT_D1, HELD_WEDNESDAY: HELD_WEDNESDAY_AT_D1}


# --- the incident, read from the record it was written into -----------------------------------
def test_the_two_incidents_are_still_in_the_committed_record():
    """Both arms of the S70 order, quoted from the manifests the live runs wrote."""
    held = json.loads((DERIVED / "manifest" / "collect-2026-08-12.json").read_text(encoding="utf-8"))
    alert = " ".join(held.get("alerts") or [])
    assert "withheld on 2026-08-11" in alert
    assert "same-weekday median 215" in alert and "55%" in alert
    assert held["volume"]["today"] == HELD_TUESDAY_AT_D1

    paged = json.loads((DERIVED / "manifest" / "collect-2026-08-10.json").read_text(encoding="utf-8"))
    assert paged["volume"] == {"today": 6, "trailing_median": 141.5, "anomalously_low": True,
                               "collection_mature": True, "comparison": "judged",
                               "maturity_reason": "the focus day cleared the readiness gate"}
    # The seam itself: the day was MATURE because a same-weekday arm cleared it, and then it was
    # judged against an all-days median twenty-three times its own Sunday norm.
    assert paged["volume"]["trailing_median"] / 6 > 20


# --- arm 1: the publication gate ----------------------------------------------------------------
def test_the_held_recess_tuesday_is_ready_the_next_morning():
    """The required outcome. 89 statements on the morning after 2026-08-11, and the gate publishes."""
    counts = _august()
    old = HELD_TUESDAY_AT_D1 / HELD_TUESDAY_OLD_BASELINE
    assert old < 0.55, "the live gate held this day"

    row = readiness.day_readiness(counts, HELD_TUESDAY)
    assert row["baseline"] == 137.0                  # the three most recent Tuesdays: 137, 126, 232
    assert row["baseline_method"] == "recent 3-week same-weekday median"
    assert row["ready"] is True and row["share"] >= readiness.READY_RATIO
    # and the day after it, held for the same reason, publishes too
    assert readiness.day_readiness(counts, HELD_WEDNESDAY)["ready"] is True


def test_the_gate_selects_the_held_tuesday_instead_of_no_opping():
    """End to end through the target selector: the run that no-opped now has a day to assemble."""
    counts = _august()
    published = {d for d in counts if d < HELD_TUESDAY}
    out = readiness.select_target_day(counts, lambda d: d in published, HELD_WEDNESDAY)
    assert out["day"] == HELD_TUESDAY
    assert out["forced"] is False, "a regime-normal day must never publish as degraded"


def test_the_recess_weekend_is_exempt_rather_than_force_finalized():
    """2026-08-01 and 2026-08-02 were the recess weekend the live gate force-finalized.

    A Saturday baseline of 8 to 11 statements cannot carry a 55 percent test: one statement moves
    the share by ten points. Three of the four force-finalized days in the whole committed record
    were weekends judged this way. The baseline is now declared unjudgeable and the day publishes
    clean instead of degraded.
    """
    counts = _august()
    for weekend_day in ("2026-08-01", "2026-08-02", RECESS_SATURDAY, RECESS_SUNDAY):
        row = readiness.day_readiness(counts, weekend_day)
        assert row["judgeable"] is False, weekend_day
        assert row["baseline"] < readiness.MIN_JUDGEABLE_BASELINE
        assert row["ready"] is True and row["share"] is None
        assert "cannot judge, do not block" in row["reason"]


def test_the_fix_only_ever_turns_a_hold_into_a_publication():
    """Monotone against the record: no day the live gate published becomes a day this one holds.

    Every committed assemble manifest carries the readiness row its run computed. Replaying the
    committed counts through the new gate may free a held day; it may never hold a freed one.
    """
    counts = _august()
    checked = 0
    for path in sorted((DERIVED / "manifest").glob("assemble-2026-0[78]-*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        recorded = manifest.get("readiness") or {}
        day = manifest.get("day")
        if recorded.get("ready") is not True or day not in counts:
            continue
        checked += 1
        assert readiness.day_readiness(counts, day)["ready"] is True, day
    assert checked >= 20, f"expected the published August record, found {checked} days"


# --- arm 2: the volume alert --------------------------------------------------------------------
def test_the_recess_sunday_that_paged_the_operator_is_quiet():
    """The 2026-08-10 page. 6 statements is a normal recess Sunday, not an incident."""
    counts = _august()
    statements = _corpus(counts)
    maturity = ops.collection_maturity(statements, RECESS_SUNDAY, reference_day="2026-08-10")
    volume = ops.volume_anomaly(statements, RECESS_SUNDAY, maturity=maturity)
    assert volume["today"] == 6
    assert volume["judgeable"] is False and volume["comparison"] == "withheld"
    assert volume["anomalously_low"] is False
    # the Saturday before it, the other false page, is quiet for the same reason
    sat = ops.collection_maturity(statements, RECESS_SATURDAY, reference_day="2026-08-09")
    assert ops.volume_anomaly(statements, RECESS_SATURDAY,
                              maturity=sat)["anomalously_low"] is False


def test_no_regime_normal_day_in_the_committed_series_pages():
    """The whole series, judged. Alert fatigue is the failure being fixed, so count the pages."""
    counts = _august()
    statements = _corpus(counts)
    paged = [day for day in sorted(counts)
             if ops.volume_anomaly(statements, day)["anomalously_low"]]
    assert paged == [], f"regime-normal days still paging: {paged}"


# --- the outage that must still be caught -------------------------------------------------------
def test_a_dead_weekday_still_holds_and_still_pages():
    """A genuine non-delivery, substituted into the real series. Both arms must fire."""
    counts = _august()
    counts[HELD_TUESDAY] = 3                       # upstream delivered almost nothing
    statements = _corpus(counts)
    row = readiness.day_readiness(counts, HELD_TUESDAY)
    assert row["ready"] is False and row["share"] < readiness.READY_RATIO
    aged = ops.collection_maturity(statements, HELD_TUESDAY, reference_day="2026-08-14")
    assert aged["mature"] is True                   # past MAX_WAIT_DAYS, upstream is not still landing
    assert ops.volume_anomaly(statements, HELD_TUESDAY, maturity=aged)["anomalously_low"] is True


def test_a_dead_weekend_pages_on_the_absolute_arm_even_though_the_ratio_is_withheld():
    """The floor withholds a RATIO on a weekend; it does not withhold the dead-man.

    A weekend baseline cannot carry a ratio, so a quiet Sunday cannot be distinguished from a
    broken one by proportion. Zero can: the quietest day in the committed record still held 2.
    """
    counts = _august()
    del counts[RECESS_SUNDAY]                       # the day delivered nothing at all
    statements = _corpus(counts)
    aged = ops.collection_maturity(statements, RECESS_SUNDAY, reference_day="2026-08-11")
    volume = ops.volume_anomaly(statements, RECESS_SUNDAY, maturity=aged)
    assert volume["today"] == 0 and volume["judgeable"] is False
    assert volume["anomalously_low"] is True
    # and it is never published as an empty page: the dataless gap stays open and self-heals
    out = readiness.select_target_day(counts, lambda d: d != RECESS_SUNDAY, "2026-08-11")
    assert out["day"] != RECESS_SUNDAY


def test_the_transport_dead_man_is_independent_of_the_volume_baseline():
    """Upstream staleness pages on its own evidence and must never route through a baseline."""
    source = ast.parse((ROOT / "pipeline" / "run_collect.py").read_text(encoding="utf-8"))
    collect = next(n for n in ast.walk(source)
                   if isinstance(n, ast.FunctionDef) and n.name == "collect")
    stale = [n for n in ast.walk(collect)
             if isinstance(n, ast.If) and "congress-press stale" in ast.unparse(n)]
    assert stale, "the upstream-staleness dead-man is gone"
    names = {n.id for n in ast.walk(stale[0]) if isinstance(n, ast.Name)}
    assert not names & {"vol", "maturity"}, "staleness must not depend on the volume baseline"
    assert run_collect.STALE_HOURS == 36.0


# --- the session regime is untouched ------------------------------------------------------------
def test_a_session_regime_day_is_judged_exactly_as_before():
    """The loudest session day in the series keeps the long arm and the same verdict.

    A recent window that ran HIGH must not raise the bar, so `expected_volume` takes the lower of
    the two arms in that direction too. 2026-07-22 ran 377 against a 232 norm; without the long
    arm capping it, the Wednesdays that follow would be judged against a one-week spike.
    """
    counts = _august()
    row = readiness.day_readiness(counts, SESSION_WEDNESDAY)
    assert row["ready"] is True
    for follower in ("2026-07-29", "2026-08-05"):
        after = readiness.day_readiness(counts, follower)
        assert after["baseline_method"].startswith("trailing"), after
        assert after["baseline"] <= readiness.same_weekday_baseline(counts, follower)
        assert after["ready"] is True


def test_the_recent_arm_needs_a_full_window_before_it_may_lower_the_bar():
    """A median over one observation IS that observation. One quiet week may not set the bar."""
    end = date(2026, 6, 10)
    counts = {(end - timedelta(days=7 * k)).isoformat(): 200 for k in range(1, 7)}
    assert readiness.expected_volume(counts, end.isoformat())["baseline"] == 200
    sparse = {(end - timedelta(days=7 * k)).isoformat(): (10 if k == 1 else 200)
              for k in (1, 4, 5, 6)}                  # only one day inside the recent window
    exp = readiness.expected_volume(sparse, end.isoformat())
    assert exp["baseline"] == 200
    assert exp["method"] == f"trailing {readiness.BASELINE_WEEKS}-week same-weekday median"


# --- one owner ----------------------------------------------------------------------------------
def test_both_arms_read_one_baseline_owner():
    """docs/37 rule 1. The gate and the alert may not hold two ideas of what a day should hold."""
    source = inspect.getsource(ops.volume_anomaly)
    assert "readiness.expected_volume" in source
    assert "statistics." not in source, "the alert must not compute a baseline of its own"

    counts = _august()
    statements = _corpus(counts)
    for day in sorted(counts):
        gate = readiness.day_readiness(counts, day)
        alert = ops.volume_anomaly(statements, day)
        assert alert["baseline"] == gate["baseline"], day
        assert alert["baseline_method"] == gate["baseline_method"], day
        assert alert["judgeable"] == gate["judgeable"], day


def test_the_two_ratios_are_read_from_their_owners_and_are_not_copies():
    """One baseline, two questions. Each arm keeps its own ratio and neither copies the other."""
    assert readiness.READY_RATIO == 0.40
    assert config.NULL_SERVICE_VOLUME_RATIO == 0.4
    assert "READY_RATIO" not in inspect.getsource(ops.volume_anomaly)
    assert "NULL_SERVICE_VOLUME_RATIO" not in inspect.getsource(readiness.day_readiness)
    assert "config.NULL_SERVICE_VOLUME_RATIO" in inspect.getsource(ops.volume_anomaly)
