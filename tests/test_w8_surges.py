"""W8 acceptance tests for surge statistics and first-observed honesty."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from pipeline import site, surges


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/w8_rankings.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_true_surge_ranks_above_stable_high_frequency_phrase():
    result = surges.build_rankings(_payload())
    surge = result["rankings"]["largest_statistical_deviations"]
    names = [row["phrase"] for row in surge]
    assert names.index("true surge phrase") < names.index("stable high frequency phrase")
    assert result["rankings"]["most_repeated"][0]["phrase"] == "stable high frequency phrase"


def test_rankings_are_separate_and_have_no_composite_score():
    result = surges.build_rankings(_payload())
    expected = {
        "method_version", "most_repeated", "largest_statistical_deviations", "qualified_surges",
        "most_skewed", "fastest_spread", "widest_family_spread",
    }
    assert set(result["rankings"]) == expected
    assert all("score" not in row for key in expected - {"method_version"}
               for row in result["rankings"][key])


def test_day_precision_tie_has_no_originator_attribution():
    entry = _payload()["ledger"]["true surge phrase"]
    observed = surges.first_observed(entry)
    assert observed["precision"] == "day"
    assert observed["ties"] == ["D2", "D3"]
    assert observed["originator_bioguide"] is None
    assert observed["lane"] == 1 and observed["corpus_start"] == "2025-01-03"


def test_first_observed_surface_discloses_lane_start_precision_and_ties():
    entry = _payload()["ledger"]["true surge phrase"]
    page = site.phrase_page_body({
        "ngram": "true surge phrase",
        "peak_units": 25,
        "first_seen": entry["first_seen"],
        "series": [{"day": "2026-07-20", "D": 2}, {"day": "2026-07-24", "D": 25}],
    })
    assert "First observed in our corpus" in page
    assert "Lane 1" in page and "corpus begins 2025-01-03" in page and "precision: day" in page
    assert "tied observations:" in page and "first observed office:" not in page


def test_documented_command_is_byte_reproducible():
    command = [sys.executable, str(ROOT / "scripts/rank_surges.py"), str(FIXTURE)]
    first = subprocess.run(command, check=True, capture_output=True).stdout
    second = subprocess.run(command, check=True, capture_output=True).stdout
    assert first == second
    parsed = json.loads(first)
    assert parsed["rankings"]["largest_statistical_deviations"][0]["phrase"] == "true surge phrase"


def test_binomial_tail_and_q_values_are_bounded():
    result = surges.build_rankings(_payload())
    rows = result["rankings"]["largest_statistical_deviations"]
    assert all(0.0 <= row["p_value"] <= row["q_value"] <= 1.0 for row in rows)
