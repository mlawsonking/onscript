"""X2 acceptance tests for denominator-calendar surge screening."""
from __future__ import annotations

from datetime import date, timedelta

from pipeline import config, surges, util


def _two_of_twenty_eight() -> dict:
    focus = date(2026, 7, 24)
    prior = [(focus - timedelta(days=value)).isoformat() for value in range(28, 0, -1)]
    denominators = {
        party: {**{day: 100 for day in prior}, focus.isoformat(): 100}
        for party in config.COMPOSITE_PARTIES
    }
    return {
        "day": focus.isoformat(),
        "denominators": denominators,
        "ledger": {
            "two day phrase": {
                "first_seen": {"date": prior[2], "precision": "day", "lane": 1},
                "daily": {
                    prior[2]: {"D": 2},
                    prior[20]: {"D": 2},
                    focus.isoformat(): {"D": 20},
                },
            }
        },
    }


def test_two_of_twenty_eight_uses_the_full_calendar_risk_set_and_proves_old_selection_differs():
    payload = _two_of_twenty_eight()
    row = surges.phrase_metrics(payload["ledger"], payload["denominators"], payload["day"])[0]
    old = surges.legacy_occurrence_baseline(
        payload["ledger"]["two day phrase"], payload["denominators"], "D", payload["day"]
    )
    assert row["baseline_calendar_days"] == 28
    assert row["baseline_observed_days"] == 28
    assert row["baseline_phrase_occurrence_days"] == 2
    assert row["baseline_successes"] == 4 and row["baseline_trials"] == 2800
    assert len(old["days"]) == 2 and old["trials"] == 200
    assert row["baseline_share"] < (old["successes"] + 0.5) / (old["trials"] + 1.0)


def test_disclosure_fields_and_provisional_gates_are_complete():
    payload = _two_of_twenty_eight()
    row = surges.phrase_metrics(payload["ledger"], payload["denominators"], payload["day"])[0]
    required = {
        "baseline_calendar_days", "baseline_observed_days", "baseline_successes",
        "baseline_trials", "absolute_change", "surge_ratio", "p_value", "q_value",
        "bh_family_definition", "bh_family_size", "screening_statistic",
        "practical_gates", "passes_practical_gate",
    }
    assert required <= set(row)
    assert row["bh_family_size"] == 1
    assert row["practical_gates"]["status"] == "provisional_frozen"


def test_weekday_option_uses_only_prior_matching_weekdays():
    payload = _two_of_twenty_eight()
    rows = surges.phrase_metrics(
        payload["ledger"], payload["denominators"], payload["day"], baseline_mode="weekday"
    )
    assert rows[0]["baseline_mode"] == "weekday"
    assert rows[0]["baseline_calendar_days"] == 4


def test_overdispersion_harness_is_deterministic_and_reports_bounded_panels():
    payload = _two_of_twenty_eight()
    first = surges.calibrate_overdispersion(payload)
    second = surges.calibrate_overdispersion(payload)
    assert first == second
    assert first["method_version"] == "surge-overdispersion-calibration-v1"
    assert first["estimates"]


def test_real_committed_phrase_uses_committed_symmetry_denominators_without_omitting_zero_days():
    phrase = util.read_json(config.DERIVED / "phrases" / "04f1b071d5f24e81.json", {})
    assert phrase.get("ngram") == "sacrifices made by those serving"
    denominator = {party: {} for party in config.COMPOSITE_PARTIES}
    for path in sorted((config.DERIVED / "symmetry").glob("2026-07-*.json")):
        report = util.read_json(path, {})
        day = report.get("day")
        if not day or day > "2026-07-24":
            continue
        for party in config.COMPOSITE_PARTIES:
            value = (report.get("parties") or {}).get(party) or {}
            count = value.get("eligible_caucus_offices", value.get("caucus_size"))
            if isinstance(count, int) and count > 0:
                denominator[party][day] = count
    daily = {row["day"]: {party: row.get(party, 0) for party in config.COMPOSITE_PARTIES}
             for row in phrase["series"]}
    ledger = {phrase["ngram"]: {"first_seen": phrase["first_seen"], "daily": daily}}
    rows = surges.phrase_metrics(ledger, denominator, "2026-07-24")
    row = next(value for value in rows if value["party"] == "D")
    assert row["baseline_calendar_days"] > row["baseline_phrase_occurrence_days"]
