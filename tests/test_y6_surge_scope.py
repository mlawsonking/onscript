"""Y6 acceptance: surge scope and ranking split (R-36.7).

Each party's baseline uses its own denominator history (no shared mutable state), and the
rankings split into qualified_surges (practical gate passed) and largest_statistical_deviations
(screening only). No surface calls a screening result a surge.
"""
from __future__ import annotations

from pipeline import instrument_fingerprint as fp
from pipeline import surges


def _divergent_payload():
    day = "2026-07-25"
    d_days = ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"]
    r_days = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04", "2026-07-05"]
    denominators = {
        "D": {**{d: 100 for d in d_days}, day: 100},
        "R": {**{r: 100 for r in r_days}, day: 100},
    }
    daily = {d: {"D": 2} for d in d_days}
    daily.update({r: {"R": 5} for r in r_days})
    daily[day] = {"D": 50, "R": 50}
    ledger = {"border security now": {"daily": daily, "first_seen": {"date": d_days[0]}}}
    return {"day": day, "denominators": denominators, "ledger": ledger}


def _gate_payload():
    day = "2026-07-25"
    prior = ["2026-07-18", "2026-07-19", "2026-07-20", "2026-07-21", "2026-07-22", "2026-07-23", "2026-07-24"]
    denominators = {"D": {**{p: 100 for p in prior}, day: 100}}
    surge_daily = {p: {"D": 1} for p in prior}
    surge_daily[day] = {"D": 80}
    modest_daily = {p: {"D": 40} for p in prior}
    modest_daily[day] = {"D": 45}
    ledger = {
        "clear surge phrase": {"daily": surge_daily, "first_seen": {"date": prior[0]}},
        "modest drift phrase": {"daily": modest_daily, "first_seen": {"date": prior[0]}},
    }
    return {"day": day, "denominators": denominators, "ledger": ledger}


def test_per_party_baselines_use_each_partys_own_denominator_history():
    payload = _divergent_payload()
    rows = surges.phrase_metrics(payload["ledger"], payload["denominators"], "2026-07-25")
    d_row = next(row for row in rows if row["party"] == "D")
    r_row = next(row for row in rows if row["party"] == "R")
    # D's baseline is summed over D's own five days (2 per day, 100 trials per day).
    assert d_row["baseline_successes"] == 10 and d_row["baseline_trials"] == 500
    # R's baseline is summed over R's own five days (5 per day). Different history, different baseline.
    assert r_row["baseline_successes"] == 25 and r_row["baseline_trials"] == 500
    assert d_row["baseline_successes"] != r_row["baseline_successes"]


def test_qualified_surges_exclude_gate_failing_screening_rows():
    rankings = surges.build_rankings(_gate_payload())["rankings"]
    deviations = {row["phrase"] for row in rankings["largest_statistical_deviations"]}
    qualified = {row["phrase"] for row in rankings["qualified_surges"]}
    assert "clear surge phrase" in qualified
    assert "modest drift phrase" in deviations       # screening keeps it
    assert "modest drift phrase" not in qualified     # the practical gate drops it
    assert qualified <= deviations                    # qualified is a strict subset
    assert all(row["passes_practical_gate"] for row in rankings["qualified_surges"])


def test_no_ranking_key_calls_a_screening_result_a_surge():
    rankings = surges.build_rankings(_gate_payload())["rankings"]
    assert "largest_surge" not in rankings
    assert "largest_statistical_deviations" in rankings
    assert "qualified_surges" in rankings


def test_the_method_version_moved_and_the_fingerprint_inherits_it():
    assert surges.METHOD_VERSION == "phrase-statistics-v3"
    # Y1 made the registry import the owning module, so the bump propagates with no registry edit.
    assert fp.method_versions()["phrase_statistics"] == "phrase-statistics-v3"
