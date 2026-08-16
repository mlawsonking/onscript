"""Y4 acceptance: deterministic nulls and state-aware posting (R-36.5).

A day with zero code-selected claims makes no model call. A day that is force-finalized
with anomalously low volume, zero eligible claims for both parties, and red instrument
status does not post party threads; one neutral service note may post instead.
"""
from __future__ import annotations

from pipeline import config, distill, llm, ops, util
from pipeline import post_bluesky as pb
from pipeline import run_collect


# --- deterministic null: zero-claim day makes no model call -----------------------------
def test_a_zero_claim_day_makes_no_model_call():
    calls = []
    saved_dry, saved_call = llm.dry_run, llm.direct_call
    try:
        llm.dry_run = lambda: False            # simulate a live key so the voice gate is armed
        llm.direct_call = lambda *a, **k: calls.append((a, k)) or {"text": "should not run"}
        line = distill.daily_line("D", "2026-05-15", [], talking_points=[], top_phrase=None,
                                  statements_by_id={}, allow_llm_voice=True)
    finally:
        llm.dry_run, llm.direct_call = saved_dry, saved_call
    assert calls == [], "the model was called on a zero-claim day"
    assert line["composite_state"] == "withheld_no_eligible_claim"
    assert line["generator"] == "deterministic"
    usage = line.get("usage") or {}
    assert (usage.get("tokens_in") or 0) == 0 and (usage.get("tokens_out") or 0) == 0


def test_the_voiceable_predicate_matches_the_withheld_state():
    assert distill._has_voiceable_content({"selected_claims": [{"id": "c1"}]}) is True
    assert distill._has_voiceable_content({"top_phrase": {"text": "border security"}}) is True
    assert distill._has_voiceable_content({"selected_claims": [], "top_phrase": None}) is False
    assert distill._has_voiceable_content({}) is False


# --- shared volume anomaly (DRY) --------------------------------------------------------
def test_volume_anomaly_is_one_shared_definition():
    assert run_collect._volume_anomaly is not None
    # 100 a day, not 10: S70 withholds the comparison under a baseline too small to carry a ratio
    # and a 10-statement norm is beneath that floor. The DRY assertion is what this test is for.
    statements = ([{"published_at": f"2026-05-{d:02d}", "lane": 1} for d in range(1, 15) for _ in range(100)]
                  + [{"published_at": "2026-05-20", "lane": 1}])
    low = ops.volume_anomaly(statements, "2026-05-20")
    assert low["anomalously_low"] is True
    assert run_collect._volume_anomaly(statements, "2026-05-20") == low
    normal = ops.volume_anomaly(statements, "2026-05-14")  # a full-volume day
    assert normal["anomalously_low"] is False


# --- state-aware posting: the four-flag decision ----------------------------------------
def test_null_service_hold_requires_all_four_conditions():
    all_true = {name: True for name in config.NULL_SERVICE_CONDITIONS}
    assert pb.null_service_hold(all_true) is True
    for name in config.NULL_SERVICE_CONDITIONS:
        one_false = dict(all_true, **{name: False})
        assert pb.null_service_hold(one_false) is False


def test_conditions_short_circuit_the_status_query_on_a_normal_day():
    # A day with no persisted service_status never triggers the live status query and never holds.
    conditions = pb.null_service_conditions({"day": "2026-05-15"})
    assert conditions["red_instrument_status"] is False
    assert pb.null_service_hold(conditions) is False


def test_a_four_flag_day_holds_both_parties_and_prepares_one_note():
    day_json = {"day": "2026-07-25", "service_status": {"conditions": {
        "force_finalized": True, "anomalously_low_volume": True,
        "zero_eligible_claims_both_parties": True}}}
    conditions = pb.null_service_conditions(day_json, red_status=True)
    assert pb.null_service_hold(conditions) is True
    held, note = pb.null_service_result("2026-07-25", ["D", "R"], note_enabled=True)
    assert set(held) == {"D", "R"}
    assert all(row["posted"] is False and row["null_service"] for row in held.values())
    assert note and "2026-07-25" in note and "today" not in note.lower()
    # dark by default: the note has no dedicated account, so the decision is what publishes
    _, dark = pb.null_service_result("2026-07-25", ["D", "R"], note_enabled=False)
    assert dark is None


def test_the_real_2026_07_25_record_meets_the_assemble_side_conditions():
    # The exact record the review cited: force-finalized with both parties withheld. The
    # committed record predates the persisted service_status block, so read the raw signals.
    day = util.read_json(config.DERIVED / "days" / "2026-07-25.json", {})
    manifest = util.read_json(config.DERIVED / "manifest" / "assemble-2026-07-25.json", {})
    assert manifest.get("forced_finalize") is True
    assert all(((day.get("daily_lines") or {}).get(p) or {}).get("composite_state")
               == "withheld_no_eligible_claim" for p in config.COMPOSITE_PARTIES)
