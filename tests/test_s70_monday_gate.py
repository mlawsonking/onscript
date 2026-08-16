"""S70-2 acceptance: the coverage arm, and what the docs/23 Monday health gate reads.

THE DEFECT. `brief.coverage` scored the NEWEST symmetry report against a trailing ALL-DAYS median.
On a Monday the newest day-scoped report is SUNDAY's, where each party lands 0 to 6 statements, and
the median it was scored against was weekday-dominated at 55 to 95. Coverage therefore read RED on
every Monday in the committed record, whatever the machine was doing:

    2026-07-20  scored 2026-07-19 Sun   D 0/82 = 0%    R 2/55   = 4%    RED
    2026-07-27  scored 2026-07-26 Sun   D 3/95 = 3%    R 0/68.5 = 0%    RED
    2026-08-03  scored 2026-08-02 Sun   D 4/87.5 = 5%  R 4/58   = 7%    RED
    2026-08-10  scored 2026-08-09 Sun   D 0/78 = 0%    R 6/55   = 11%   RED

docs/23 section 7.3 conditions every scheduled flip on the Monday digest being green, so that arm
alone made the gate unpassable. It was never seen, because S68-5 found the Monday digest had never
been delivered: the latin-1 header defect ate every send since the flag flipped. The first Monday
digest that can actually arrive is 2026-08-17.

The first test below is the decisive one and uses NO projection: it replays the 2026-08-10 Monday
from the committed symmetry series alone. The live brief read RED that morning. The fixed arm reads
GREEN off Friday 2026-08-07, on measured numbers, naming the two weekend days it skipped.

The later tests project 2026-08-11 through 2026-08-16 forward, and say so. Every projected day is
`median(that party's last three same-weekdays) x that party's recess factor`, where the factor is
measured from 2026-08-10, the one recess weekday the record actually holds. The projection's pooled
totals run above the two recess days that were observed (102 and 108 against 96 and 86), so it
flatters the arms rather than the reverse.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import json
import statistics
import tempfile
from pathlib import Path

from pipeline import brief, config, ops, readiness

ROOT = Path(__file__).resolve().parents[1]
PARTIES = ("D", "R")
RECESS_MONDAY = "2026-08-10"          # the one recess weekday with a committed symmetry report
GATE_MONDAY = "2026-08-17"


@contextlib.contextmanager
def _derived(files: dict):
    """A synthetic derived tree with ntfy stubbed. Tests never write into the real data/derived."""
    real_derived, real_ntfy = config.DERIVED, ops.ntfy
    with tempfile.TemporaryDirectory() as d:
        config.DERIVED = Path(d)
        ops.ntfy = lambda *a, **k: {"sent": True}
        try:
            for rel, obj in files.items():
                f = config.DERIVED / rel.replace("__", "/")
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps(obj), encoding="utf-8")
            yield
        finally:
            config.DERIVED, ops.ntfy = real_derived, real_ntfy


def _committed_symmetry() -> dict:
    """Day-scoped committed symmetry reports, whole rows. Production-shaped input, never asserted
    equal to a fresh build (docs/37 rules 2 and 3)."""
    out = {}
    for path in sorted((ROOT / "data" / "derived" / "symmetry").glob("2026-*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("day_scoped") and row.get("day"):
            out[row["day"]] = row
    return out


def _ingest(rows: dict, day: str, party: str):
    return ((rows.get(day, {}).get("parties") or {}).get(party) or {}).get("statements_ingested")


def _last3(rows: dict, day: str, party: str):
    d0 = dt.date.fromisoformat(day)
    vals = [_ingest(rows, (d0 - dt.timedelta(days=7 * k)).isoformat(), party) for k in (1, 2, 3)]
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None


def _recess_factors(rows: dict) -> dict:
    return {p: _ingest(rows, RECESS_MONDAY, p) / _last3(rows, RECESS_MONDAY, p) for p in PARTIES}


def _projected(rows: dict, factors: dict) -> dict:
    """The committed rows plus 2026-08-11 .. 2026-08-16 under the stated projection rule.

    Claims figures are CARRIED from the same weekday rather than modelled, so the verifier arm is
    neither flattered nor invented: it reads what that weekday last really did."""
    out = dict(rows)
    for k in range(1, 7):
        day = (dt.date.fromisoformat(RECESS_MONDAY) + dt.timedelta(days=k)).isoformat()
        prior = (dt.date.fromisoformat(day) - dt.timedelta(days=7)).isoformat()
        parties = {}
        for p in PARTIES:
            src = ((out.get(prior, {}).get("parties") or {}).get(p) or {})
            parties[p] = {
                "statements_ingested": max(0, round(_last3(out, day, p) * factors[p])),
                "claims_published": src.get("claims_published", 0),
                "claims_dropped": src.get("claims_dropped", 0)}
        out[day] = {"day": day, "day_scoped": True, "parties": parties}
    return out


def _fixture(rows: dict, *, today: str, published_through: str, age_hours: float = 4.0) -> dict:
    files = {}
    for day, row in rows.items():
        files[f"symmetry__{day}.json"] = row
        if day <= published_through:
            files[f"manifest__assemble-{day}.json"] = {"kind": "assemble", "day": day,
                                                       "degraded": False,
                                                       "forced_finalize": False}
    files[f"manifest__collect-{today}.json"] = {"source_freshness": {"ok": True,
                                                                     "age_hours": age_hours}}
    files[f"cost__{today[:7]}.json"] = {"month": today[:7],
                                        "days": {f"{today[:7]}-01": {"usd": 0.05}}}
    return files


# --- the decisive test: committed data only ------------------------------------------------------
def test_the_monday_that_read_red_reads_green_on_committed_data():
    """2026-08-10, replayed from the committed symmetry series with nothing projected."""
    rows = _committed_symmetry()
    assert RECESS_MONDAY in rows, "the committed symmetry series should still hold the Monday"

    # The defect, stated as the arithmetic that produced it. The newest report that Monday is
    # Sunday's, and neither party's Sunday volume can carry a comparison with weekday-dominated days.
    sunday = "2026-08-09"
    for p in PARTIES:
        assert _ingest(rows, sunday, p) <= 6

    with _derived(_fixture(rows, today=RECESS_MONDAY, published_through="2026-08-09")):
        cv = brief.coverage(RECESS_MONDAY)
    assert cv["status"] == "green", cv["note"]
    assert cv["day"] == "2026-08-07", cv["note"]        # Friday, the newest judgeable day
    assert cv["skipped_days"] == ["2026-08-09", "2026-08-08"]
    assert "skipped" in cv["note"] and "a ratio needs" in cv["note"]
    for p in PARTIES:
        assert cv["parties"][p]["status"] == "green"
        assert cv["parties"][p]["share"] >= brief.COVERAGE_MIN_SHARE
    # named, not silent: the note carries the day it scored, its age, and both parties' numbers
    assert "2026-08-07 (3d)" in cv["note"] and "D " in cv["note"] and "R " in cv["note"]


def test_a_weekend_baseline_is_withheld_rather_than_answered():
    """Per-party weekend baselines are 1.5 to 4 statements. No ratio can carry that."""
    rows = _committed_symmetry()
    series = {p: {d: _ingest(rows, d, p) for d in rows if _ingest(rows, d, p) is not None}
              for p in PARTIES}
    for p in PARTIES:
        for weekend in ("2026-08-09", "2026-08-08", "2026-08-02", "2026-08-01"):
            exp = readiness.expected_volume(series[p], weekend)
            assert exp["judgeable"] is False, (p, weekend, exp)
    # and a weekday in the same series is judgeable, so the floor is not simply muting everything
    for p in PARTIES:
        assert readiness.expected_volume(series[p], "2026-08-07")["judgeable"] is True


def test_a_one_party_ingest_break_still_reads_red_on_a_scored_weekday():
    """The detector coverage exists for. Same committed series, one party zeroed on the scored day."""
    rows = {d: json.loads(json.dumps(r)) for d, r in _committed_symmetry().items()}
    rows["2026-08-07"]["parties"]["R"]["statements_ingested"] = 0
    with _derived(_fixture(rows, today=RECESS_MONDAY, published_through="2026-08-09")):
        cv = brief.coverage(RECESS_MONDAY)
    assert cv["day"] == "2026-08-07"
    assert cv["parties"]["R"]["status"] == "red" and cv["parties"]["D"]["status"] == "green"
    assert cv["status"] == "red"


def test_the_stale_reporting_guard_is_untouched():
    """The guard this module earned: reports that STOP ARRIVING are unknown, not scored off an
    older healthy day. The judgeable walk must not have quietly become a staleness bypass."""
    rows = {d: r for d, r in _committed_symmetry().items() if d <= "2026-08-05"}
    with _derived(_fixture(rows, today=RECESS_MONDAY, published_through="2026-08-05")):
        cv = brief.coverage(RECESS_MONDAY)
    assert cv["status"] == "unknown"
    assert "cannot describe current coverage" in cv["note"]


def test_the_scored_day_may_not_drift_past_its_bound():
    """The walk is bounded. Enough consecutive unjudgeable days and coverage is UNKNOWN, not a
    scored week-old number wearing a green."""
    rows = {d: json.loads(json.dumps(r)) for d, r in _committed_symmetry().items()}
    for row in rows.values():                        # every baseline in the series goes below floor
        for p in PARTIES:
            row["parties"][p]["statements_ingested"] = 1
    with _derived(_fixture(rows, today=RECESS_MONDAY, published_through="2026-08-09")):
        cv = brief.coverage(RECESS_MONDAY)
    assert cv["status"] == "unknown"
    assert "coverage is not measured" in cv["note"]
    # the walk stops at MAX_SCORED_AGE_DAYS rather than reaching for an older number to score
    assert cv["skipped_days"] == ["2026-08-09", "2026-08-08", "2026-08-07", "2026-08-06"]
    assert len(cv["skipped_days"]) == brief.MAX_SCORED_AGE_DAYS


def test_coverage_reads_the_s70_baseline_owner():
    """docs/37 rule 1 across all three arms: the gate, the volume alert, and now coverage."""
    import inspect
    source = inspect.getsource(brief)
    assert "readiness.expected_volume" in source
    assert "statistics" not in source, "coverage must not keep a median of its own"


# --- the Monday 2026-08-17 gate, with the projection stated --------------------------------------
def test_the_2026_08_17_gate_arms_are_predicted_and_the_streak_heals():
    """Every arm the docs/23 section 7.3 health gate reads, on the drained-backlog Monday.

    Push Thursday evening, then the gate publishes 08-11 and 08-12 on Friday's two passes, 08-13 and
    08-14 on Saturday's, 08-15 on Sunday's, and 08-16 on Monday's own run before the brief is built
    (`_owners_brief` is called after `assemble` in `run_assemble.main`). So the Monday brief sees
    days published through 08-16.
    """
    rows = _committed_symmetry()
    factors = _recess_factors(rows)
    assert 0.7 < factors["D"] < 0.9 and 0.4 < factors["R"] < 0.6, factors
    projected = _projected(rows, factors)

    with _derived(_fixture(projected, today=GATE_MONDAY, published_through="2026-08-16")):
        b = brief.build_brief(GATE_MONDAY)
    arms = {n["name"]: n for n in b["numbers"]}

    # STREAK HEALS. Days published late but ready-and-unforced are publishes, not misses: the arm
    # reads the assemble manifests, and a drained backlog leaves no hole for it to find.
    assert arms["streak"]["status"] == "green", arms["streak"]["note"]
    assert arms["streak"]["last_missed"] is None
    assert arms["streak"]["value"] >= 7

    # COVERAGE scores Friday 08-14, skipping the two weekend days by name.
    cv = arms["coverage"]
    assert cv["day"] == "2026-08-14"
    assert cv["skipped_days"] == ["2026-08-16", "2026-08-15"]
    assert cv["parties"]["D"]["status"] == "green"       # D holds 0.82 of its own recess-era norm
    # R is the arm that decides this Monday, and on the one observed recess weekday it ran 0.52 of
    # its own same-weekday norm. That is a TRUE statement about R's recess volume, not an instrument
    # artifact, so it is asserted as measured rather than tuned away.
    assert cv["parties"]["R"]["share"] < brief.COVERAGE_MIN_SHARE
    assert cv["status"] == "red"

    # VERIFIER_DROP is independently red and predates this order (docs/39 M5, docs/26 Session 69's
    # watch item): the recess thins the denominator, and the carried claims give 7 published against
    # 13 dropped over the window.
    assert arms["verifier_drop"]["status"] == "red"
    assert arms["spend"]["status"] == "green"
    assert arms["reach"]["status"] == "manual"

    # So the gate pauses, and it pauses on two arms this order did not create.
    assert b["headline"] == "RED: coverage, verifier_drop", b["headline"]
    assert b["reds"] == ["coverage", "verifier_drop"]


def test_the_R_arm_is_the_hinge_and_its_break_even_is_measured():
    """Where the Monday coverage verdict turns, so the packet quotes a number and not a hunch."""
    rows = _committed_symmetry()
    factors = _recess_factors(rows)
    flips = {}
    for r_factor in (0.45, 0.50, 0.55, 0.60, 0.65, 0.75, 1.00):
        projected = _projected(rows, {"D": factors["D"], "R": r_factor})
        with _derived(_fixture(projected, today=GATE_MONDAY, published_through="2026-08-16")):
            cv = brief.coverage(GATE_MONDAY)
        flips[r_factor] = cv["status"]
        assert cv["day"] == "2026-08-14"                 # the scored day never moves
    assert flips[0.45] == "red" and flips[0.55] == "red"
    assert flips[0.60] == "green" and flips[1.00] == "green"
    # The break-even sits between an R recess factor of 0.55 and 0.60; the one observed recess
    # weekday measured 0.52. D never falls below the floor at any point in this sweep.
