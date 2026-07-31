"""The committed pilot record verifies against itself (docs/37 rules 2 and 3).

These tests read the real committed pilot artifacts, not fixtures, because the seals and the
coverage claims are the evidence the gold set rests on and only production-shaped data proves
them. They are internal-consistency checks over pinned history: each artifact is asserted
against the identity it recorded when it was written, never against a fresh build from the
live tree. That distinction is docs/37 rule 3, and it is exactly the trap the sample seal
verifier falls into (recorded in evaluation/goldset/PILOT-RECORD.md).
"""
import csv
import hashlib
import io
import json
from pathlib import Path

from pipeline import config

GOLDSET = Path(config.REPO_ROOT) / "evaluation" / "goldset"
BUNDLE = GOLDSET / "bundles" / "pilot"
SEALED_SEAL = "7facc4d2323596a71153997fda33a924324634f1a096c5dee2df221ec86a00d3"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path):
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sheet(path):
    rows = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
    return [r for r in rows if (r.get("candidate_id") or "").strip()]


def _rendered_text(path):
    """The bytes as the renderer hashed them: LF in the text, CRLF on disk under Windows."""
    return path.read_text(encoding="utf-8", newline="").replace("\r\n", "\n")


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sealed_ids():
    return [row["candidate_id"] for row in _json(GOLDSET / "pilot.sample.json")["candidates"]]


def test_every_pilot_artifact_names_one_sealed_sample():
    manifest = _json(GOLDSET / "MANIFEST.json")
    assert manifest["seal_hash"] == SEALED_SEAL
    assert manifest["pilot_size"] == 200
    for name in ("pilot.sample.json",):
        assert _json(GOLDSET / name)["seal_hash"] == SEALED_SEAL
    for name in ("model-rater.run.json", "model-rater.plan.json"):
        assert _json(BUNDLE / name)["seal_hash"] == SEALED_SEAL, name
    assert len(_sealed_ids()) == 200
    assert len(set(_sealed_ids())) == 200


def test_the_model_rater_sheet_matches_the_seal_its_run_recorded():
    run = _json(BUNDLE / "model-rater.run.json")
    sheet = BUNDLE / "model-rater.answersheet.csv"
    assert run["sheet_sha256"] == _sha256(_rendered_text(sheet))
    assert run["sheet_rows"] == 200
    assert run["sheet_complete"] is True
    assert run["errors"] == []
    assert run["sheet_validation"] == []
    assert run["labels"] == 200 and run["items_expected"] == 200
    assert run["cost_usd"] == 0.0


def test_the_model_rater_instrument_is_the_registered_frozen_prompt():
    """The run and the plan both recorded the Y9 registration, field for field.

    Pinned history: this compares the two committed manifests with each other and with the
    registration as it stood when they were written. A later deliberate re-freeze of the live
    registration does not and must not break it.
    """
    run = _json(BUNDLE / "model-rater.run.json")["registration"]
    plan = _json(BUNDLE / "model-rater.plan.json")["registration"]
    frozen_at_run_time = {
        "prompt_id": "GS1",
        "prompt_version": "v1.0",
        "wrapper_sha256": "90e0661f52ad3f8c2943b0e07242ff6c6c03bba9fc7ef1ec11e767cf8b3402cc",
        "guide_sha256": "2243cddef095cc30e5eb39fe1c7689cbe444e409593d1f4b020891b046e0daf2",
        "rating_prompt_sha256":
            "1aa8447702f2b163103a3f23fc7447ebece81395189e1a6c2bbae885144a8246",
    }
    for field, value in frozen_at_run_time.items():
        assert run[field] == value, f"run manifest {field}"
        assert plan[field] == value, f"plan {field}"
    assert _json(BUNDLE / "model-rater.plan.json")["instrument_drift"] == []
    assert _json(BUNDLE / "model-rater.plan.json")["registration_frozen"] is True


def test_the_transport_records_the_reader_beside_the_registered_model():
    run = _json(BUNDLE / "model-rater.run.json")
    assert run["transport"] == "session"
    assert run["registered_model"] == "claude-sonnet-5"
    assert run["reader_model"] == "claude-opus-5"
    assert run["frozen_prompt_rater_id"] == "model-rater-GS1-v1.0"
    assert run["rater_id"] == "model-rater-GS1-v1.0-claude-opus-5"
    # Absent rather than a fabricated zero (S60 variance 5).
    assert "not applicable" in run["token_accounting"]


def test_the_model_rater_covers_the_sealed_200_through_every_carrier():
    sealed = sorted(_sealed_ids())
    run = _json(BUNDLE / "model-rater.run.json")
    requests = _jsonl(BUNDLE / "model-rater.requests.jsonl")
    worksheet = _jsonl(BUNDLE / "model-rater.session-worksheet.jsonl")
    answers = _jsonl(BUNDLE / "model-rater.session-answers.jsonl")
    sheet = _sheet(BUNDLE / "model-rater.answersheet.csv")

    assert sorted(r["candidate_id"].strip() for r in sheet) == sealed
    assert sorted(a["candidate_id"] for a in answers) == sealed
    assert sorted(cid for r in requests for cid in r["candidate_ids"]) == sealed
    assert [r["candidate_ids"] for r in worksheet] == [r["candidate_ids"] for r in requests]
    assert [r["index"] for r in worksheet] == list(range(len(worksheet)))
    assert sum(len(r["item_request_sha256"]) for r in worksheet) == 200
    assert len(run["calls"]) == len(requests) == 148
    assert sum(c["items"] for c in run["calls"]) == 200
    assert sum(c["labels_returned"] for c in run["calls"]) == 200
    assert all(c["item_request_sha256"] for c in run["calls"])


def test_pass_one_is_a_complete_human_pass_over_the_sealed_200():
    """Michael's pass 1: 200 of 200 labelled, every id sealed, no duplicates, no extras.

    Coverage only. Pass 1 was performed under an inverted standard and is preserved as a
    calibration record, never as gold (PILOT-RECORD.md). Nothing here reads it as an answer key.
    """
    rows = _sheet(BUNDLE / "michael-pass1.answersheet.csv")
    ids = [r["candidate_id"].strip() for r in rows]
    assert len(rows) == 200
    assert sorted(ids) == sorted(_sealed_ids())
    assert len(set(ids)) == 200
    assert all((r["gold_class"] or "").strip() for r in rows)
    assert all((r["gold_family_id"] or "").strip() for r in rows)
    assert _sha256(_rendered_text(BUNDLE / "michael-pass1.answersheet.csv")) == (
        "51e65e0fbd57b9b33518875e0bf2b4011576d0f37f1290bc0bda412e3ac1d7ea")


def test_pass_one_carries_the_inversion_the_ruling_names():
    """The three measurements the pass-1 ruling rests on, pinned so they cannot drift.

    These are calibration facts about a preserved record, not metrics: no denominator here is
    an accuracy, an agreement, or a reliability statistic.
    """
    rows = _sheet(BUNDLE / "michael-pass1.answersheet.csv")
    classes = [r["gold_class"].strip() for r in rows]
    message = [r for r in rows if r["gold_class"].strip() == "message"]

    # The guide's stated safe default was never once chosen.
    assert classes.count("unknown") == 0
    assert classes.count("message") == 155
    # The completeness gate is a necessary condition for message, and it went unanswered.
    assert sum(1 for r in message if not (r.get("phrase_complete") or "").strip()) == 141
    # Three items were labelled message while completeness was answered no.
    assert sum(1 for r in message
               if (r.get("phrase_complete") or "").strip().lower() == "false") == 3


def test_the_blank_pass_one_template_stays_blank():
    """michael.answersheet.csv is the N5 blank template. Labels live in the pass-1 file."""
    rows = _sheet(BUNDLE / "michael.answersheet.csv")
    assert len(rows) == 200
    assert not any((r["gold_class"] or "").strip() for r in rows)
    assert not any((r["gold_family_id"] or "").strip() for r in rows)
