"""R1: the live side of the replay is read, not generated, and the gate population is honest.

These tests are built from the real committed day records rather than fixtures alone, because
the finding they protect only exists in production data: the committed days span five prompt
lineages and two stats schemas, and a harness that ignores that seam reports a gate population
an order of magnitude larger than the one R-33.6 actually asks for (docs/37 rules 2 and 13).
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from pipeline import config, contracts, distill, llm, shadow_replay, site


ROOT = Path(__file__).resolve().parent.parent
DAYS = ROOT / "data" / "derived" / "days"


def _lines():
    for path in sorted(DAYS.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for party in config.COMPOSITE_PARTIES:
            line = (payload.get("daily_lines") or {}).get(party)
            if isinstance(line, dict):
                yield payload.get("day") or path.stem, party, line


def test_the_live_side_is_the_committed_record_and_never_calls_a_model():
    original = llm.direct_call
    llm.direct_call = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("the record side of the replay called the API"))
    try:
        report = shadow_replay.run(DAYS)
    finally:
        llm.direct_call = original
    assert report["comparison_design"].startswith("the live side is the committed production record")
    for row in report["party_day_results"]:
        assert row["live"]["source"] == "committed_production_record"
        assert row["live"]["tokens_in"] == 0 and row["live"]["cost_usd"] == 0.0
        payload = json.loads((DAYS / f"{row['day']}.json").read_text(encoding="utf-8"))
        recorded = payload["daily_lines"][row["party"]]["composite"]
        assert row["live"]["composite"] == recorded, (
            "the live side must be what production published, byte for byte")


def test_the_cost_projection_prices_only_the_generated_side():
    plan = shadow_replay.plan(DAYS)
    assert plan["cost_projection"]["calls"] == plan["ladder"]["gate_eligible_party_days"]
    assert "read from the committed record" in plan["cost_projection"]["calls_basis"]


def test_the_eligibility_ladder_states_every_exclusion_against_the_real_record():
    plan = shadow_replay.plan(DAYS)
    ladder = plan["ladder"]
    assert ladder["committed_day_files"] >= ladder["days_with_both_composites"]
    assert ladder["party_days_with_composites"] == (
        ladder["days_with_both_composites"] * len(config.COMPOSITE_PARTIES))
    assert ladder["gate_eligible_party_days"] <= ladder["party_days_with_composites"]
    for row in plan["party_day_plan"]:
        assert row["eligible"] == (not row["exclusion_reasons"])
        for reason in row["exclusion_reasons"]:
            assert reason in {"no_composite", "prompt_lineage_mismatch", "not_model_generated",
                              "stats_schema_mismatch", "stats_digest_mismatch"}


def test_a_record_from_an_earlier_prompt_lineage_is_excluded_not_counted():
    seen = False
    for _, _, line in _lines():
        verdict = shadow_replay.classify_record(line)
        pair = shadow_replay.PROMPT_PAIRS[verdict["prompt_id"]][0]
        live_sha = shadow_replay._prompt(verdict["prompt_id"], "live")["sha256"]
        if line.get("prompt_sha") != live_sha:
            seen = True
            assert "prompt_lineage_mismatch" in verdict["exclusion_reasons"], (
                f"a record written by a prompt other than {pair} was admitted to the gate")
    assert seen, "the committed corpus no longer contains an earlier lineage to prove this on"


def test_a_deterministic_or_dry_run_record_is_not_a_sample_of_the_prompt():
    seen = False
    for _, _, line in _lines():
        if line.get("generator") not in site.PRODUCTION_GENERATORS:
            seen = True
            assert "not_model_generated" in shadow_replay.classify_record(line)["exclusion_reasons"]
    assert seen, "the committed corpus no longer contains a template-voice day to prove this on"
    # The generator allowlist is read from its owning module, never copied here.
    assert "sonnet_direct" in site.PRODUCTION_GENERATORS


def test_a_pre_claim_binding_stats_block_cannot_feed_the_candidate_prompt():
    legacy = {"composite": "x", "generator": "sonnet_direct", "quiet": False,
              "prompt_sha": shadow_replay._prompt("P2", "live")["sha256"],
              "stats": {"party": "D", "day": "2026-07-01", "statements": 4, "talking_points": []}}
    verdict = shadow_replay.classify_record(legacy)
    assert verdict["exclusion_reasons"] == ["stats_schema_mismatch"]
    assert contracts.SCHEMA_VERSION == 2


def test_a_tampered_stats_block_is_caught_by_its_recorded_digest():
    for _, _, line in _lines():
        request = line.get("structured_request") or {}
        if not request.get("stats_sha256"):
            continue
        tampered = json.loads(json.dumps(line))
        tampered["stats"]["statements"] = (tampered["stats"].get("statements") or 0) + 1
        assert "stats_digest_mismatch" in shadow_replay.classify_record(tampered)["exclusion_reasons"]
        return
    raise AssertionError("no committed record carries a stats digest to prove this on")


def test_gate_progress_rides_on_every_artifact_with_its_denominators():
    plan = shadow_replay.plan(DAYS)
    report = shadow_replay.run(DAYS)
    for artifact in (plan, report):
        progress = artifact["gate_progress"]
        assert progress["requirement"] == "R-33.6"
        assert progress["complete_days"]["required"] == 60
        assert progress["party_days"]["required"] == 200
        assert progress["estimator"] and progress["unit"] and progress["denominator"]
        assert progress["complete_days"]["fraction"] == round(
            progress["complete_days"]["observed"] / 60, 6)
        assert progress["party_days"]["remaining"] == max(
            0, 200 - progress["party_days"]["observed"])
    assert report["activation_gate"]["minimum_sample_passed"] is False
    assert report["activation_gate"]["ready"] is False


def test_the_dry_comparison_scores_exactly_the_eligible_party_days():
    report = shadow_replay.run(DAYS)
    plan = shadow_replay.plan(DAYS)
    assert report["window"]["scored_party_days"] == plan["ladder"]["gate_eligible_party_days"]
    assert len(report["party_day_results"]) == report["window"]["scored_party_days"]
    excluded = {(row["day"], row["party"]) for row in report["excluded_party_days"]}
    scored = {(row["day"], row["party"]) for row in report["party_day_results"]}
    assert not (excluded & scored)
    assert len(excluded) + len(scored) == plan["ladder"]["party_days_with_composites"]


def test_the_plan_is_deterministic_and_carries_no_clock():
    first = json.dumps(shadow_replay.plan(DAYS), sort_keys=True)
    second = json.dumps(shadow_replay.plan(DAYS), sort_keys=True)
    assert first == second
    for token in ("generated_at", "updated_at", "timestamp"):
        assert token not in first


def test_the_plan_cli_runs_free_without_a_key_and_reports_the_count_plainly():
    completed = subprocess.run(
        [sys.executable, "scripts/shadow_replay.py", "--plan", "--days-dir", str(DAYS)],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    plan = json.loads(completed.stdout)
    assert plan["method_version"] == shadow_replay.METHOD_VERSION
    assert plan["ladder"]["gate_eligible_days"] == plan["gate_progress"]["complete_days"]["observed"]
    assert plan["gate_progress"]["passed"] is False


def test_the_candidate_prompt_renders_from_the_stats_production_used():
    for day, party, line in _lines():
        if not shadow_replay.classify_record(line)["eligible"]:
            continue
        request = shadow_replay.candidate_request(line, day, party)
        assert "{selected_claims_json}" not in request["user"]
        assert str(line["stats"]["statements"]) in request["user"]
        assert request["request_sha256"] == shadow_replay.request_sha256(
            request["system"], request["user"])
        return
    raise AssertionError("no eligible party-day to render")


def test_the_record_side_reports_a_moved_verifier_verdict_instead_of_smoothing_it():
    for _, _, line in _lines():
        if not shadow_replay.classify_record(line)["eligible"]:
            continue
        side = shadow_replay.record_side(line)
        assert side["verifier_verdict_moved"] == (
            side["recorded_verifier_passed"] is not None
            and bool(side["recorded_verifier_passed"]) != side["verifier_passed"])
        assert side["output_sha256"] == distill._record_hash(
            {"composite": side["composite"], "sentence_claims": line.get("sentence_claims")})
        return
    raise AssertionError("no eligible party-day to score")
