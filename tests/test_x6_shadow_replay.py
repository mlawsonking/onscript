"""X6 dry-first shadow replay and activation gate.

Updated in R1 for the corrected comparison economics: the live side is the committed
production record and only the candidate side is generated (see test_r1_replay_economics).
The gate behaviour asserted here is unchanged, because R1 changed what counts toward the
gate, never the gate itself.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from pipeline import config, llm, shadow_replay


ROOT = Path(__file__).resolve().parent.parent
DAYS = ROOT / "data" / "derived" / "days"


def test_committed_days_run_end_to_end_and_emit_the_full_comparison_report():
    report = shadow_replay.run(DAYS)
    plan = shadow_replay.plan(DAYS)
    assert report["mode"] == "dry_run"
    assert report["ladder"]["days_with_both_composites"] == len(shadow_replay._complete_days(DAYS))
    assert report["window"]["scored_party_days"] == plan["ladder"]["gate_eligible_party_days"]
    assert report["minimums"] == {"complete_days": 60, "party_days": 200}
    assert set(report["prompt_inventory"]) == {"P2", "P3"}
    assert set(report["candidate"]["guard_violation_party_days"]) == set(shadow_replay.GUARD_NAMES)
    assert report["candidate"]["fallback_rate_denominator"] == report["window"]["scored_party_days"]
    assert report["activation_gate"]["minimum_sample_passed"] is False
    assert report["activation_gate"]["ready"] is False
    assert report["activation_gate"]["dry_run_cannot_activate"] is True
    assert len(report["party_day_results"]) == report["window"]["scored_party_days"]


def test_dry_run_never_calls_the_api_even_when_a_key_exists():
    original = llm.direct_call
    llm.direct_call = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("dry shadow replay touched the API")
    )
    try:
        report = shadow_replay.run(DAYS, live=False, allow_api_spend=True)
    finally:
        llm.direct_call = original
    assert report["mode"] == "dry_run"
    assert report["actual_cost_usd"] == 0.0
    assert all(row["live"]["tokens_in"] == 0 for row in report["party_day_results"])
    assert all(row["candidate"]["tokens_in"] == 0 for row in report["party_day_results"])


def test_live_mode_requires_the_second_explicit_spend_authorization():
    original = llm.direct_call
    llm.direct_call = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("unauthorized live replay touched the API")
    )
    try:
        try:
            shadow_replay.run(DAYS, live=True, allow_api_spend=False, limit=1)
        except PermissionError as error:
            assert "allow_api_spend" in str(error)
        else:
            raise AssertionError("live replay did not fail closed")
    finally:
        llm.direct_call = original


def test_documented_cli_runs_dry_and_emits_json_without_a_key():
    completed = subprocess.run(
        [sys.executable, "scripts/shadow_replay.py", "--days-dir", str(DAYS)],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    report = json.loads(completed.stdout)
    assert report["mode"] == "dry_run"
    assert report["fallback_rate_ceiling"] == config.SHADOW_FALLBACK_RATE_CEILING
    assert report["gate_progress"]["passed"] is False


def test_prompt_pairs_pin_live_and_candidate_lineages_without_moving_live_defaults():
    inventory = shadow_replay.prompt_inventory()
    assert inventory["P2"]["live"]["file"] == "P2_daily_line.v1.3.txt"
    assert inventory["P2"]["candidate"]["file"] == "P2_daily_line.v1.4.txt"
    assert inventory["P3"]["live"]["file"] == "P3_quiet_day.v1.1.txt"
    assert inventory["P3"]["candidate"]["file"] == "P3_quiet_day.v1.2.txt"
    assert llm._PROMPT_FILES["P2"] == inventory["P2"]["live"]["file"]
    assert llm._PROMPT_FILES["P3"] == inventory["P3"]["live"]["file"]


def test_each_zero_tolerance_guard_detects_its_named_failure():
    claim_one = {
        "claim_id": "c1", "object_type": "phrase_claim",
        "label": "protect voting rights now", "quote": "protect voting rights now",
        "topics": ["elections"],
        "counts": {"offices": 3, "publications": 4, "families": 3},
    }
    claim_two = {
        "claim_id": "c2", "object_type": "phrase_claim",
        "label": "lower prescription drug costs", "quote": "lower prescription drug costs",
        "topics": ["health"],
        "counts": {"offices": 3, "publications": 3, "families": 3},
    }
    stats = {
        "selected_claims": [claim_one, claim_two],
        "talking_points": [claim_one, claim_two],
        "claim_ids": ["c1", "c2"],
    }
    output = {
        "composite": (
            '3 offices carried "protect voting rights now". '
            '"protect voting rights now" and "lower prescription drug costs" appeared together. '
            'Elections defined the day. '
            'We also quoted "we protect voting rights now".'
        ),
        "sentence_claims": [],
    }
    guards = shadow_replay._guard_results(output, stats)
    assert guards["unit_mixing"]
    assert guards["quote_extension"] == ["we protect voting rights now"]
    assert guards["topic_label_assertion"] == ["elections"]
    assert guards["multi_claim_sentence"] == [1]
    assert guards["sentence_mapping_mismatch"] is True
