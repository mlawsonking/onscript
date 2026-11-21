"""S74-11 Package 4 (F4): holidays do not read as upstream failure.

Replayed on the committed discipline series (data/derived/discipline.json, D+R+I statements per
day: the counts the corpus actually held), the current gate force-finalized eight real days at the
2025 year end (12-24, 12-25, 12-26, 12-29, 12-30, 12-31, 01-01, 01-02) and two at Thanksgiving
(11-27, 11-28), each degraded and alerting "upstream never filled". The committed holiday calendar
(config.HOLIDAY_*) extends the S70 regime mechanism in readiness.expected_volume: a holiday day that
is CLOSED is not held for volume. A day that is not closed, and every non-holiday day, is judged
exactly as before, so the dead-man still holds and forces a real collapse.

The replay model is the audit's (sim_readiness2 FULL): two assemble runs per calendar day R, product
day P = R-1, every day fully landed at first look. Each run reads a collect manifest shaped like the
committed ones: generated at R 10:41Z against an upstream push at R 09:32Z.
"""
from __future__ import annotations

import inspect
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pipeline import config, ops, post_bluesky, readiness, run_assemble

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"


# D+R+I statements per day, 2025-10-01 through 2026-01-15, as data/derived/discipline.json held them
# at commit time (2026-11-21). Frozen here as pinned history (docs/37 rule 3): the live series is
# rewritten by every collect, and a late upstream backfill must not be able to erase the incident.
_FROZEN_START = date(2025, 10, 1)
_FROZEN = [int(v) for v in (
    "271 91 160 17 12 86 212 158 222 186 12 7 40 100 133 133 133 8 4 102 140 153 191 171 14 10 127 "
    "162 175 190 159 13 5 105 125 135 167 178 12 51 169 74 309 155 117 7 6 129 338 238 320 264 14 8 "
    "133 145 61 12 9 5 3 142 215 214 285 168 13 4 148 200 331 355 222 15 15 148 235 364 368 207 13 6 "
    "127 85 16 6 12 5 1 47 30 17 4 23 170 6 72 142 188 393 196 10 10 172 197 288 286").split()]


def _committed_counts() -> dict[str, int]:
    return {(_FROZEN_START + timedelta(days=i)).isoformat(): v for i, v in enumerate(_FROZEN)}


def _live_counts() -> dict[str, int]:
    series = json.loads((DERIVED / "discipline.json").read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for party in config.ALL_PARTIES:
        for day, row in (series.get(party) or {}).items():
            if isinstance(row, dict) and isinstance(row.get("statements"), int):
                counts[day] = counts.get(day, 0) + row["statements"]
    return counts


def test_the_frozen_counts_are_the_committed_series_shape():
    """Production-shaped input (docs/37 rule 2): the live committed series still covers the window
    and still agrees with the frozen literals on the holiday days that matter, within a tolerance
    a late upstream backfill could not break silently."""
    live = _live_counts()
    frozen = _committed_counts()
    assert all(day in live for day in frozen)
    for day in ("2025-12-24", "2025-12-25", "2026-01-01", "2026-01-03"):
        assert abs(live[day] - frozen[day]) <= max(5, frozen[day] // 5), (day, live[day], frozen[day])


def test_the_live_series_year_end_has_no_forced_holiday_day():
    """The healed invariant, asserted on the live file: inside the committed windows, no day of the
    2025 year end is force-finalized when closure evidence is present."""
    rows = _replay("2025-12-15", "2026-01-10", _live_counts())
    assert not [r["day"] for r in rows if r["forced"] and readiness.holiday_regime(r["day"])]


def _collect_manifest(run_day: date) -> dict:
    iso = run_day.isoformat()
    return {"kind": "collect", "generated_at": f"{iso}T10:41:00Z",
            "source_freshness": {"ok": True, "pushed_at": f"{iso}T09:32:00Z", "age_hours": 1.1}}


def _replay(start: str, end: str, counts: dict, *, closure: bool = True) -> list[dict]:
    final = {k for k in counts if k < (date.fromisoformat(start) - timedelta(days=1)).isoformat()}
    out = []
    run_day = date.fromisoformat(start)
    while run_day <= date.fromisoformat(end):
        product = (run_day - timedelta(days=1)).isoformat()
        view = {k: v for k, v in counts.items() if k <= product}
        manifest = _collect_manifest(run_day)
        for _ in range(2):
            sel = readiness.select_target_day(
                view, lambda d: d in final, product,
                closed=(lambda d: readiness.day_closed(d, manifest)) if closure else None)
            if sel["day"]:
                final.add(sel["day"])
                out.append({"run": run_day.isoformat(), **sel})
        run_day += timedelta(days=1)
    return out


def test_the_calendar_is_the_committed_one():
    assert readiness.thanksgiving(2025) == date(2025, 11, 27)
    assert readiness.thanksgiving(2026) == date(2026, 11, 26)
    assert readiness.thanksgiving(2027) == date(2027, 11, 25)
    assert [readiness.holiday_regime(f"2026-11-{d:02d}") for d in range(24, 31)] == [
        None, "thanksgiving", "thanksgiving", "thanksgiving", "thanksgiving",
        "thanksgiving", None]
    assert readiness.holiday_regime("2026-12-23") is None
    assert readiness.holiday_regime("2026-12-24") == "year-end"
    assert readiness.holiday_regime("2027-01-02") == "year-end"
    assert readiness.holiday_regime("2027-01-03") is None
    assert readiness.holiday_regime("2026-07-04") is None


def test_the_current_gate_forced_the_eight_year_end_days_the_audit_named():
    """The incident, reproduced on the committed counts with no closure evidence (today's gate)."""
    rows = _replay("2025-12-15", "2026-01-10", _committed_counts(), closure=False)
    forced = sorted(r["day"] for r in rows if r["forced"])
    assert forced == ["2025-12-24", "2025-12-25", "2025-12-26", "2025-12-29", "2025-12-30",
                      "2025-12-31", "2026-01-01", "2026-01-02"], forced


def test_the_real_year_end_replays_with_zero_forced_days():
    counts = _committed_counts()
    rows = _replay("2025-12-15", "2026-01-10", counts)
    assert not [r["day"] for r in rows if r["forced"]]
    published = {r["day"]: r for r in rows}
    day = date(2025, 12, 14)
    while day <= date(2026, 1, 9):
        iso = day.isoformat()
        assert iso in published, iso  # no hole
        row = published[iso]
        lag = (date.fromisoformat(row["run"]) - day).days
        if readiness.holiday_regime(iso):
            assert row["readiness"]["regime"] == "holiday"
            assert row["readiness"]["count"] == counts.get(iso, 0)
            assert row["readiness"]["closed"] is True
            assert lag == 1, (iso, lag)  # the normal schedule: the first run after the day
        else:
            assert "regime" not in row["readiness"]
        day += timedelta(days=1)
    # 2026-01-03 (170 statements) is no longer published two days late behind the held days.
    assert (date.fromisoformat(published["2026-01-03"]["run"]) - date(2026, 1, 3)).days == 1


def test_thanksgiving_2025_replays_without_forcing_the_window():
    counts = _committed_counts()
    before = _replay("2025-11-20", "2025-12-05", counts, closure=False)
    assert sorted(r["day"] for r in before if r["forced"]) == ["2025-11-26", "2025-11-27", "2025-11-28"]
    rows = _replay("2025-11-20", "2025-12-05", counts)
    forced = sorted(r["day"] for r in rows if r["forced"])
    # R-74.12: the Wednesday before (61 statements against a 164 same-weekday baseline, 37
    # percent) is inside the window, so nothing in the week is forced and nothing publishes late.
    assert forced == [], forced
    for iso in ("2025-11-26", "2025-11-27", "2025-11-28", "2025-11-29", "2025-11-30"):
        row = next(r for r in rows if r["day"] == iso)
        assert row["forced"] is False and row["readiness"]["regime"] == "holiday"


def test_a_non_holiday_collapse_still_holds_and_forces_as_today():
    counts = _committed_counts()
    collapsed = dict(counts)
    collapsed["2025-11-18"] = 3   # a session Tuesday (the committed count is 338) that never landed
    for closure in (True, False):
        rows = _replay("2025-11-16", "2025-11-24", collapsed, closure=closure)
        row = next(r for r in rows if r["day"] == "2025-11-18")
        assert row["forced"] is True
        assert (date.fromisoformat(row["run"]) - date(2025, 11, 18)).days == 3
        assert "regime" not in row["readiness"]
    # Held, not published, on the runs before the wait expires.
    view = {k: v for k, v in collapsed.items() if k <= "2025-11-19"}
    manifest = _collect_manifest(date(2025, 11, 20))
    sel = readiness.select_target_day(view, lambda d: d < "2025-11-18", "2025-11-19",
                                      closed=lambda d: readiness.day_closed(d, manifest))
    assert sel["day"] is None and "not ready" in sel["reason"]


def test_a_holiday_day_that_never_closes_is_judged_as_before():
    """Upstream silent through the holiday: no push after the day, so the day is not closed, the
    gate holds it and forces it exactly as today. The dead-man path does not depend on the calendar."""
    counts = _committed_counts()
    stale = {"generated_at": "2025-12-27T10:41:00Z",
             "source_freshness": {"ok": True, "pushed_at": "2025-12-24T09:32:00Z"}}
    view = {k: v for k, v in counts.items() if k <= "2025-12-26"}
    sel = readiness.select_target_day(view, lambda d: d < "2025-12-24", "2025-12-26",
                                      closed=lambda d: readiness.day_closed(d, stale))
    assert sel["day"] == "2025-12-24" and sel["forced"] is True
    assert sel["readiness"]["regime"] == "holiday" and sel["readiness"]["closed"] is False


def test_closure_needs_a_collect_and_a_push_after_the_day_ends_in_new_york():
    assert readiness.day_end_utc("2025-12-25") == datetime(2025, 12, 26, 5, tzinfo=timezone.utc)
    assert readiness.day_end_utc("2026-07-04") == datetime(2026, 7, 5, 4, tzinfo=timezone.utc)
    after = {"generated_at": "2025-12-26T10:00:00Z", "source_freshness": {"pushed_at": "2025-12-26T09:30:00Z"}}
    assert readiness.day_closed("2025-12-25", after)
    assert not readiness.day_closed("2025-12-25", {**after, "generated_at": "2025-12-26T04:59:00Z"})
    assert not readiness.day_closed("2025-12-25", {**after, "source_freshness": {"pushed_at": "2025-12-26T04:00:00Z"}})
    assert not readiness.day_closed("2025-12-25", {"generated_at": "2025-12-26T10:00:00Z",
                                                   "source_freshness": {"ok": True, "note": "offline"}})
    assert not readiness.day_closed("2025-12-25", None)
    # Production-shaped, frozen here: the two collect manifests production wrote on 2026-11-21.
    # The file itself is rewritten by every collect of the day (S74-12: reading it live made this
    # test fail as soon as the second collect landed; docs/37 rule 3), so its fields are pinned.
    first = {"generated_at": "2026-11-21T00:53:00Z",
             "source_freshness": {"ok": True, "pushed_at": "2026-11-20T14:43:00Z"}}
    assert readiness.day_closed("2026-11-19", first)
    assert not readiness.day_closed("2026-11-20", first)
    second = {"generated_at": "2026-11-21T16:52:27Z",
              "source_freshness": {"ok": True, "pushed_at": "2026-11-21T13:19:51Z", "age_hours": 3.54}}
    assert readiness.day_closed("2026-11-20", second)
    assert not readiness.day_closed("2026-11-21", second)
    # The live file still has the shape the gate reads.
    live = json.loads((DERIVED / "manifest" / "collect-latest.json").read_text(encoding="utf-8"))
    assert readiness._utc(live["generated_at"]) and readiness._utc(live["source_freshness"]["pushed_at"])


def test_the_forced_alert_states_what_is_known():
    counts = _committed_counts()
    view = {k: v for k, v in counts.items() if k <= "2025-12-26"}
    sel = readiness.select_target_day(view, lambda d: d < "2025-12-24", "2025-12-26")
    assert sel["forced"] is True
    assert "never filled" not in sel["reason"]
    assert "16 statements" in sel["reason"] and "held 2 product days" in sel["reason"]
    assert "baseline of" in sel["reason"]
    summary = readiness.forced_summary(sel["readiness"])
    assert summary.startswith("16 statements") and "holiday regime (year-end)" in summary
    assert "never filled" not in inspect.getsource(run_assemble)
    assert "never filled" not in inspect.getsource(readiness.select_target_day)
    # The production gate call reads closure from the committed collect manifest.
    main = inspect.getsource(run_assemble.main)
    assert '"collect-latest.json"' in main and "readiness.day_closed(d, collect_manifest)" in main


def _holiday_day_json(forced: bool, zero_claims: bool, statements: list[dict], day: str) -> dict:
    """The service_status block exactly as run_assemble.assemble computes it."""
    return {"service_status": {"rule": config.NULL_SERVICE_RULE, "conditions": {
        "force_finalized": bool(forced),
        "anomalously_low_volume": bool(ops.volume_anomaly(statements, day)["anomalously_low"]),
        "zero_eligible_claims_both_parties": zero_claims,
    }}}


def test_a_closed_holiday_day_posts_and_a_zero_claim_one_follows_r_36_5():
    counts = _committed_counts()
    statements = [{"published_at": k, "lane": 1} for k, v in counts.items()
                  if "2025-11-01" <= k <= "2025-12-25" for _ in range(v)]
    view = {k: v for k, v in counts.items() if k <= "2025-12-25"}
    manifest = _collect_manifest(date(2025, 12, 26))
    sel = readiness.select_target_day(view, lambda d: d < "2025-12-25", "2025-12-25",
                                      closed=lambda d: readiness.day_closed(d, manifest))
    assert sel["day"] == "2025-12-25" and sel["forced"] is False
    with_claims = post_bluesky.null_service_conditions(
        _holiday_day_json(sel["forced"], False, statements, "2025-12-25"), red_status=True)
    assert post_bluesky.null_service_hold(with_claims) is False
    # Zero eligible claims: R-36.5 is evaluated unchanged on the persisted conditions. Its
    # force_finalized condition is False for a closed holiday day, so R-36.5 does not hold it.
    zero = post_bluesky.null_service_conditions(
        _holiday_day_json(sel["forced"], True, statements, "2025-12-25"), red_status=True)
    assert zero["zero_eligible_claims_both_parties"] is True
    assert post_bluesky.null_service_hold(zero) is all(zero[c] for c in config.NULL_SERVICE_CONDITIONS)
    # The same day, unclosed and forced, keeps every R-36.5 input it has today.
    forced_json = _holiday_day_json(True, True, statements, "2025-12-25")
    assert forced_json["service_status"]["conditions"]["anomalously_low_volume"] is True
    assert post_bluesky.null_service_hold(
        post_bluesky.null_service_conditions(forced_json, red_status=True)) is True


def test_the_collect_alert_does_not_page_a_holiday_ratio_but_still_pages_zero():
    counts = _committed_counts()
    statements = [{"published_at": k, "lane": 1} for k, v in counts.items()
                  if "2025-11-01" <= k <= "2025-12-25" for _ in range(v)]
    mature = {"mature": True, "reason": "test"}
    alert = ops.volume_anomaly(statements, "2025-12-25", maturity=mature)
    assert alert["regime"] == "holiday" and alert["anomalously_low"] is False
    assert alert["comparison"] == "withheld"
    empty = [s for s in statements if s["published_at"] != "2025-12-25"]
    assert ops.volume_anomaly(empty, "2025-12-25", maturity=mature)["anomalously_low"] is True
    # Outside the calendar the ratio arm pages exactly as before.
    thin = [s for s in statements if s["published_at"] != "2025-12-23"] + [
        {"published_at": "2025-12-23", "lane": 1}] * 3
    assert ops.volume_anomaly(thin, "2025-12-23", maturity=mature)["anomalously_low"] is True
