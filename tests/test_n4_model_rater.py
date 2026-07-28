"""N4 acceptance: the frozen-prompt model rater (docs/35 section 10.2).

The rating instrument is content-addressed before anyone can spend on it, the requests carry
the same blinded context the human packet carries and nothing else, and the parser refuses
anything that is not a valid label for an expected item. The registration is a pin, not a
captured record: it must equal the live instrument, and an edit to the guide or the wrapper
that is not re-frozen fails here exactly as a live run would refuse.
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline import (config, goldset_bundle, goldset_metrics, goldset_rater as rater, llm,
                      util)


PILOT_PATH = Path(config.REPO_ROOT) / "evaluation" / "goldset" / "pilot.sample.json"


def _candidates(count: int = 6) -> list[dict]:
    sample = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    return sample["candidates"][:count]


def _item(candidate: dict) -> dict:
    return {
        "candidate_id": candidate["candidate_id"],
        "phrase": candidate["ngram"],
        "before": "A prior sentence.",
        "sentence": f"A sentence carrying {candidate['ngram']} in context.",
        "after": "A following sentence.",
        "title": "A release title",
        "office": f"{candidate['party']}-XX House",
        "date": candidate["day"],
        "support": [],
    }


def _items_by_id(candidates):
    return {row["candidate_id"]: _item(row) for row in candidates}


def test_the_registration_reads_its_live_owners():
    live = rater.registration()
    assert live["wrapper_sha256"] == util.sha256_hex(rater.wrapper_text())
    assert live["guide_sha256"] == util.sha256_hex(rater.guide_text())
    assert live["rating_prompt_sha256"] == rater.rating_prompt_sha256()
    assert live["prompt_file"] == "pipeline/prompts/GS1_gold_rater.v1.0.txt"
    assert live["model"] in llm.PRICING


def test_the_committed_registration_is_the_live_instrument():
    # A pin, not a captured record. If the guide or the wrapper changed without a re-freeze,
    # the published sheet would not be reproducible, so this failing is the intended alarm.
    assert rater.registration_drift(rater.load_registration()) == []


def test_a_guide_edit_drifts_the_registration_and_refuses_a_live_run():
    frozen = rater.load_registration()
    original = rater._GUIDE_TEXT
    try:
        rater._GUIDE_TEXT = original + "\nan unregistered rule\n"
        drift = rater.registration_drift(frozen)
        assert "guide_sha256" in drift and "rating_prompt_sha256" in drift
        try:
            rater.assert_registered(frozen)
        except rater.RegistrationError as error:
            assert "re-freeze" in str(error)
        else:
            raise AssertionError("a drifted instrument was allowed to spend")
    finally:
        rater._GUIDE_TEXT = original
    assert rater.registration_drift(frozen) == []


def test_a_missing_registration_refuses_rather_than_defaulting():
    original = rater.REGISTRATION_PATH
    try:
        rater.REGISTRATION_PATH = Path(config.REPO_ROOT) / "evaluation" / "goldset" / "nope.json"
        try:
            rater.load_registration()
        except rater.RegistrationError as error:
            assert "freeze the prompt before spending" in str(error)
        else:
            raise AssertionError("a missing registration did not refuse")
    finally:
        rater.REGISTRATION_PATH = original


def test_the_request_carries_the_guide_and_the_blinded_context_only():
    candidates = _candidates(1)
    request = rater.build_requests(candidates, _items_by_id(candidates))[0]
    assert rater.guide_text() in request["system"]
    assert "{guide}" not in request["system"]
    assert candidates[0]["candidate_id"] in request["user"]
    assert candidates[0]["ngram"] in request["user"]
    assert "{items}" not in request["user"] and "{count}" not in request["user"]
    # The system side is the authored guide, which is public. The item side is where a machine
    # signal could leak, so it carries no machine field name and no machine-decided value.
    # Field names and machine-minted identifiers only: the item block quotes real speech, so
    # ordinary words like "priority" or "split" are not usable as leak probes.
    user = request["user"].lower()
    for probe in ("predicted_class", "predicted_family_id", "classifier_rule", "impact_tags",
                  "family_evidence_count", "member_headcount", "dfam:", "dfrev:", "sha256:"):
        assert probe not in user, f"the model rater saw a machine signal: {probe}"
    assert candidates[0]["classifier_rule"].lower() not in user
    assert candidates[0]["predicted_family_id"].lower() not in user


def test_requests_group_by_day_and_party_and_are_deterministic():
    candidates = _candidates(8)
    items = _items_by_id(candidates)
    first = rater.build_requests(candidates, items)
    second = rater.build_requests(list(reversed(candidates)), items)
    assert first == second
    for request in first:
        for cid in request["candidate_ids"]:
            match = next(row for row in candidates if row["candidate_id"] == cid)
            assert (match["day"], match["party"]) == (request["group_day"], request["group_party"])
    assert sum(len(request["candidate_ids"]) for request in first) == len(candidates)


def test_the_estimate_is_an_upper_bound_and_costs_nothing_to_produce(monkeypatch=None):
    candidates = _candidates(4)
    requests = rater.build_requests(candidates, _items_by_id(candidates))
    original = llm.direct_call

    def _refuse(*args, **kwargs):
        raise AssertionError("the dry path must never call the API")

    try:
        llm.direct_call = _refuse
        estimate = rater.estimate_run(requests, on_date="2026-07-28")
    finally:
        llm.direct_call = original
    assert estimate["requests"] == len(requests)
    assert estimate["items"] == len(candidates)
    assert estimate["estimated_cost_usd"] > 0
    assert estimate["approx_tokens_in"] > 0


def test_the_parser_accepts_valid_lines_and_names_every_problem():
    ids = ["cand:aaa", "cand:bbb", "cand:ccc"]
    text = "\n".join([
        "Here are my labels.",
        json.dumps({"candidate_id": "cand:aaa", "gold_class": "message",
                    "gold_family_id": "f1", "phrase_complete": True,
                    "proposition_consistent": None, "stance": "affirmative",
                    "claim_supported": False, "notes": "close call"}),
        json.dumps({"candidate_id": "cand:bbb", "gold_class": "not-a-class",
                    "gold_family_id": "f1"}),
        json.dumps({"candidate_id": "cand:zzz", "gold_class": "message",
                    "gold_family_id": "f9"}),
        "{ broken json",
    ])
    rows, errors = rater.parse_response(text, ids)
    assert [row["candidate_id"] for row in rows] == ["cand:aaa"]
    assert rows[0]["phrase_complete"] == "true"
    assert rows[0]["proposition_consistent"] == ""
    assert rows[0]["stance"] == "affirmative"
    assert rows[0]["claim_supported"] == "false"
    assert any("invalid gold_class" in error for error in errors)
    assert any("unexpected candidate_id" in error for error in errors)
    assert any("unparseable line" in error for error in errors)
    # bbb answered invalidly and is reported as invalid; ccc never answered at all. Both are
    # named, and neither reaches the sheet.
    assert any("cand:ccc: no label returned" in error for error in errors)
    assert len(errors) == 4


def test_an_out_of_range_stance_is_dropped_not_invented():
    rows, _errors = rater.parse_response(
        json.dumps({"candidate_id": "cand:aaa", "gold_class": "unknown",
                    "gold_family_id": "f1", "stance": "sarcastic"}), ["cand:aaa"])
    assert rows[0]["stance"] == ""


def test_the_model_sheet_is_the_sheet_the_intake_tool_ingests():
    candidates = _candidates(3)
    ids = [row["candidate_id"] for row in candidates]
    text = "\n".join(
        json.dumps({"candidate_id": cid, "gold_class": "message", "gold_family_id": "f1",
                    "phrase_complete": True, "stance": "affirmative"})
        for cid in ids)
    rows, errors = rater.parse_response(text, ids)
    assert errors == []
    csv_text = rater.render_answer_csv(rows)
    assert csv_text.splitlines()[0] == ",".join(goldset_bundle.ANSWER_COLUMNS)
    parsed = goldset_metrics.read_answer_csv(csv_text, rater.rater_id())
    assert goldset_metrics.validate_rows(parsed) == []
    assert {row["candidate_id"] for row in parsed} == set(ids)
    assert all(row["annotator_id"] == rater.rater_id() for row in parsed)


def test_the_rater_id_pins_the_frozen_prompt():
    assert rater.rater_id() == f"model-rater-{rater.PROMPT_ID}-{rater.PROMPT_VERSION}"
