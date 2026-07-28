"""R2: the live replay is frozen, preflighted, and scored before it is ever allowed to spend.

The order these tests pin is the point: freeze the instrument, clear the budget, then call. A
run that spent first and froze afterward could publish a sheet produced by a prompt nobody
registered (docs/35 section 10.2, docs/37 rules 6 and 7).
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from pipeline import config, llm, ops, shadow_replay


ROOT = Path(__file__).resolve().parent.parent
DAYS = ROOT / "data" / "derived" / "days"


def _eligible_pair():
    for row in shadow_replay.plan(DAYS)["party_day_plan"]:
        if row["eligible"]:
            return row["day"], row["party"]
    raise AssertionError("no gate-eligible party-day in the committed corpus")


def _stub_call(text):
    def call(model, system, user, *, max_tokens=400):
        return {"text": text, "tokens_in": 120, "tokens_out": 40}
    return call


# --- the frozen instrument ----------------------------------------------------------

def test_the_frozen_registration_matches_its_live_owners():
    frozen = shadow_replay.load_registration()
    assert shadow_replay.registration_drift(frozen) == []
    assert frozen["replay_prompt_sha256"] == shadow_replay.replay_prompt_sha256()
    assert frozen["minimums"] == {"complete_days": 60, "party_days": 200}
    assert frozen["fallback_rate_ceiling"] == config.SHADOW_FALLBACK_RATE_CEILING
    assert frozen["model"] == llm.VOICE_MODEL


def test_an_edited_candidate_prompt_refuses_the_run_before_it_can_spend():
    frozen = shadow_replay.load_registration()
    original = shadow_replay._P2_CANDIDATE_TEXT
    llm_original = llm.direct_call
    llm.direct_call = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("a drifted replay instrument reached the API"))
    try:
        shadow_replay._P2_CANDIDATE_TEXT = original + "\nquietly added instruction"
        drift = shadow_replay.registration_drift(frozen)
        assert "replay_prompt_sha256" in drift
        assert "prompt_inventory.P2.candidate" in drift
        try:
            shadow_replay.assert_registered(frozen)
        except shadow_replay.RegistrationError as error:
            assert "re-freeze" in str(error)
        else:
            raise AssertionError("a drifted replay instrument did not fail closed")
    finally:
        shadow_replay._P2_CANDIDATE_TEXT = original
        llm.direct_call = llm_original
    assert shadow_replay.registration_drift(frozen) == []


def test_a_missing_registration_refuses_rather_than_spending_unregistered():
    original = shadow_replay.REGISTRATION_PATH
    try:
        shadow_replay.REGISTRATION_PATH = Path("does-not-exist-replay-registration.json")
        try:
            shadow_replay.load_registration()
        except shadow_replay.RegistrationError as error:
            assert "freeze the replay prompts before spending" in str(error)
        else:
            raise AssertionError("a missing registration did not fail closed")
    finally:
        shadow_replay.REGISTRATION_PATH = original


# --- the budget preflight -----------------------------------------------------------

def test_the_preflight_reads_the_real_ledger_and_the_real_ceilings():
    preflight = shadow_replay.budget_preflight(0.01, bound_usd=3.0, day="2026-07-28")
    assert preflight["monthly_code_ceiling_usd"] == config.LLM_MONTHLY_CEILING_USD
    assert preflight["month_to_date_usd"] == ops.month_to_date_usd("2026-07-28", include_day=True)
    assert preflight["headroom_usd"] == round(
        config.LLM_MONTHLY_CEILING_USD - preflight["month_to_date_usd"], 6)
    assert preflight["required_headroom_usd"] == 6.0


def test_headroom_below_twice_the_bound_blocks_even_a_tiny_projection():
    preflight = shadow_replay.budget_preflight(0.01, bound_usd=4.6, day="2026-07-28")
    assert "headroom_below_twice_the_bound" in preflight["blocking_reasons"]
    assert preflight["cleared"] is False


def test_a_projection_over_the_authorized_bound_blocks():
    preflight = shadow_replay.budget_preflight(3.5, bound_usd=3.0, day="2026-07-28")
    assert "projection_exceeds_authorized_bound" in preflight["blocking_reasons"]


def test_a_missing_key_is_named_by_the_preflight_not_discovered_mid_run():
    preflight = shadow_replay.budget_preflight(0.01, bound_usd=3.0, day="2026-07-28")
    assert preflight["api_key_available"] is not llm.dry_run()
    if llm.dry_run():
        assert "no_api_key" in preflight["blocking_reasons"]
        try:
            shadow_replay.run(DAYS, live=True, allow_api_spend=True, day="2026-07-28")
        except shadow_replay.BudgetPreflightError as error:
            assert "no_api_key" in str(error)
        else:
            raise AssertionError("a keyless live run was not refused by the preflight")


# --- the live path, exercised without spending --------------------------------------

def test_the_live_path_scores_a_well_formed_candidate_against_the_record():
    day, party = _eligible_pair()
    reply = json.dumps({"composite": "We released 3 statements today.",
                        "sentence_claims": [{"sentence_idx": 0, "claim_ids": []}]})
    report = shadow_replay.run(DAYS, live=False, only={(day, party)})
    assert report["window"]["scored_party_days"] == 1
    payload = json.loads((DAYS / f"{day}.json").read_text(encoding="utf-8"))
    line = payload["daily_lines"][party]
    request = shadow_replay.candidate_request(line, day, party)
    scored = shadow_replay.candidate_side(request, line, live=True, call=_stub_call(reply))
    assert scored["source"] == "generated_live"
    assert scored["tokens_in"] == 120 and scored["tokens_out"] == 40
    assert scored["cost_usd"] == llm.estimate_cost(llm.VOICE_MODEL, 120, 40, batched=False)
    assert scored["request_sha256"] == request["request_sha256"]
    assert scored["response_sha256"] == shadow_replay.util.sha256_hex(reply)
    assert scored["verifier_passed"] is True
    assert all(not value for value in scored["guards"].values())
    assert scored["fallback"] is False


def test_a_candidate_reply_that_is_not_json_counts_as_a_fallback():
    day, party = _eligible_pair()
    payload = json.loads((DAYS / f"{day}.json").read_text(encoding="utf-8"))
    line = payload["daily_lines"][party]
    request = shadow_replay.candidate_request(line, day, party)
    scored = shadow_replay.candidate_side(
        request, line, live=True, call=_stub_call("We released 3 statements today."))
    assert scored["fallback"] is True, (
        "the v1.4 contract is JSON only; a prose reply is a fallback, not a pass")


def test_the_fallback_rate_is_scored_against_the_preregistered_ceiling():
    report = shadow_replay.run(DAYS)
    assert report["fallback_rate_ceiling"] == 0.05
    rate = report["candidate"]["fallback_rate"]
    assert report["activation_gate"]["fallback_rate_passed"] == (
        rate is not None and rate <= 0.05)
    assert report["candidate"]["fallback_rate_estimator"] == (
        "fallback party-days / offered party-days")
    assert report["candidate"]["fallback_rate_unit"] == "party-day share"


def test_the_zero_tolerance_score_covers_all_four_named_checks_plus_the_verifier():
    report = shadow_replay.run(DAYS)
    guards = report["candidate"]["guard_violation_party_days"]
    for name in ("unit_mixing", "quote_extension", "topic_label_assertion",
                 "multi_claim_sentence"):
        assert name in guards
    assert report["activation_gate"]["zero_tolerance_checks_passed"] == (
        bool(report["party_day_results"])
        and report["candidate"]["verifier_failed"] == 0
        and all(value == 0 for value in guards.values()))


# --- the evidence file --------------------------------------------------------------

def test_the_evidence_file_admits_only_real_model_responses():
    dry_rows = shadow_replay.evidence_rows(shadow_replay.run(DAYS))
    assert dry_rows and all(row["mode"] == "dry_run" for row in dry_rows)
    with tempfile.TemporaryDirectory() as raw:
        try:
            shadow_replay.append_evidence(dry_rows, Path(raw))
        except ValueError as error:
            assert "only real model responses are evidence" in str(error)
        else:
            raise AssertionError("dry rows were admitted to the replay evidence file")
        assert shadow_replay.load_evidence(Path(raw)) == []


def test_evidence_rows_carry_the_request_hash_and_both_scored_sides():
    rows = shadow_replay.evidence_rows(shadow_replay.run(DAYS))
    for row in rows:
        assert len(row["request_sha256"]) == 64
        assert len(row["response_sha256"]) == 64
        assert row["replay_prompt_sha256"] == shadow_replay.replay_prompt_sha256()
        assert set(row["record"]) >= {"composite", "verifier_passed", "guards", "fallback"}
        assert set(row["candidate"]) >= {"composite", "verifier_passed", "guards", "fallback"}
        assert row["candidate_prompt"]["version"] in ("1.4", "1.2")
