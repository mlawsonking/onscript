"""N3 acceptance: single-human-rater intake with model triage (docs/35 section 10).

One human rates; the model reads a second time for triage only. The tests hold three
promises: the agreement is never named or shaped like inter-annotator agreement, the model
never writes a gold label, and every artifact carries the mandatory provenance label. The
last test runs the whole flow over the committed sealed pilot rather than a fixture, because
only production-shaped input proves the integration (docs/37 rule 2).
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline import config, eligibility, goldset_single as single


PILOT_PATH = Path(config.REPO_ROOT) / "evaluation" / "goldset" / "pilot.sample.json"
PROTOCOL_PATH = Path(config.REPO_ROOT) / "docs" / "35-ANNOTATION-PROTOCOL.md"


def _candidates(count: int = 12) -> list[dict]:
    """Real sealed candidates, so day, party, and family fields are production shaped."""
    sample = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    return sample["candidates"][:count]


def _all_keys(payload) -> set[str]:
    keys: set[str] = set()
    stack = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            keys.update(str(key).lower() for key in node)
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return keys


def _sheet(candidates, classes, families, annotator):
    return [
        {"candidate_id": row["candidate_id"], "annotator_id": annotator,
         "gold_class": classes[index % len(classes)],
         "gold_family_id": families[index % len(families)]}
        for index, row in enumerate(candidates)
    ]


def test_the_protocol_document_quotes_the_label_the_code_owns():
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    assert single.PROVENANCE_LABEL in text
    assert "goldset_single.PROVENANCE_LABEL" in text


def test_the_label_is_the_ruled_wording():
    assert single.PROVENANCE_LABEL == "author-annotated, single human rater, provisional"


def test_an_inter_annotator_field_is_refused_anywhere_in_the_payload():
    for payload in (
        {"inter_annotator_agreement": 0.9},
        {"tasks": {"surface_class": {"inter-rater": 0.9}}},
        {"rows": [{"annotator_agreement": 1}]},
    ):
        try:
            single.assert_no_inter_annotator_claim(payload)
        except ValueError:
            continue
        raise AssertionError(f"payload was not refused: {payload}")
    single.assert_no_inter_annotator_claim({"human_versus_model_agreement": {"items": 3}})


def test_the_prose_may_deny_the_claim_the_field_names_may_not_make_it():
    # The interpretation text says the forbidden words in order to rule them out. Only field
    # names are scanned, so the denial can ship while the claim cannot.
    assert "not agreement between two humans" in single.INTERPRETATION
    single.assert_no_inter_annotator_claim({"interpretation": single.INTERPRETATION})


def test_the_agreement_report_labels_itself_and_claims_no_gate():
    candidates = _candidates()
    human = _sheet(candidates, ["message", "unknown"], ["fam-1", "fam-2"], "michael")
    model = _sheet(candidates, ["message", "procedural"], ["fam-1", "fam-2"], "model-rater")
    report = single.human_versus_model_report(
        human, model, candidates, human_rater="michael", model_rater="model-rater",
        sample="pilot")

    assert "human_versus_model_agreement" in report
    assert report["provenance"]["label"] == single.PROVENANCE_LABEL
    assert report["provenance"]["human_raters"] == 1
    assert report["provenance"]["gate_b_claimed"] is False
    assert report["provenance"]["pilot_gates_evaluated"] is False
    assert report["pilot_gates"]["evaluated"] is False
    # No reliability statistic is reported as a field. The omission note names them in prose,
    # which is the denial, not the claim.
    keys = _all_keys(report)
    assert not any("kappa" in key or "alpha" in key or "pass" in key for key in keys)
    assert "reliability_statistics_omitted" in report


def test_the_agreement_numbers_are_observed_counts_with_denominators():
    candidates = _candidates(4)
    human = _sheet(candidates, ["message"], ["fam-1"], "michael")
    model = _sheet(candidates, ["message", "message", "unknown", "message"], ["fam-1"],
                   "model-rater")
    report = single.human_versus_model_report(
        human, model, candidates, human_rater="michael", model_rater="model-rater")
    entry = report["human_versus_model_agreement"]["surface_class"]
    assert entry == {"items": 4, "agreed": 3, "disagreed": 1, "observed_agreement": 0.75}


def test_the_triage_queue_separates_disagreement_from_a_missing_reading():
    candidates = _candidates(3)
    human = _sheet(candidates, ["message"], ["fam-1"], "michael")
    model = [
        {**human[0], "annotator_id": "model-rater", "gold_class": "procedural"},
        {**human[1], "annotator_id": "model-rater", "gold_family_id": "fam-9"},
    ]
    queue = single.triage_queue(human, model, candidates)
    reasons = {row["candidate_id"]: row["reason"] for row in queue}
    assert reasons[candidates[0]["candidate_id"]] == "class"
    assert reasons[candidates[1]["candidate_id"]] == "family"
    assert reasons[candidates[2]["candidate_id"]] == "no model reading"
    # Only real disagreements need a decision from the human.
    assert single.triage_required_ids(queue) == {
        candidates[0]["candidate_id"], candidates[1]["candidate_id"]}


def test_triage_validation_refuses_an_unresolved_or_malformed_decision():
    required = {"cand:1", "cand:2"}
    errors = single.validate_triage(
        [{"candidate_id": "cand:1", "resolution": "revise", "gold_class": "nope",
          "gold_family_id": "", "notes": ""}], required)
    assert any("valid gold_class" in error for error in errors)
    assert any("needs a gold_family_id" in error for error in errors)
    assert any("cand:2" in error and "no triage decision" in error for error in errors)
    ok = single.validate_triage(
        [{"candidate_id": "cand:1", "resolution": "keep", "gold_class": "", "gold_family_id": "",
          "notes": ""},
         {"candidate_id": "cand:2", "resolution": "revise", "gold_class": "unknown",
          "gold_family_id": "fam-2", "notes": ""}], required)
    assert ok == []


def test_the_model_never_writes_a_gold_label():
    candidates = _candidates(2)
    human = _sheet(candidates, ["message"], ["fam-1"], "michael")
    model = _sheet(candidates, ["private"], ["fam-9"], "model-rater")
    queue = single.triage_queue(human, model, candidates)
    assert len(queue) == 2
    # The human keeps his own label on both. The model's disagreement changes nothing.
    triage = [{"candidate_id": row["candidate_id"], "resolution": "keep", "gold_class": "",
               "gold_family_id": "", "notes": ""} for row in queue]
    final = single.apply_triage(human, triage)
    assert [row["gold_class"] for row in final] == ["message", "message"]
    assert {row["annotation_status"] for row in final} == {"human-kept-after-triage"}
    merged = single.merge_records(candidates, final)
    assert all(record["adjudicator_id"] is None for record in merged["records"])
    assert all(record["annotator_ids"] == ["michael"] for record in merged["records"])
    assert all(record["gold_class"] == "message" for record in merged["records"])


def test_a_revision_is_the_humans_own_second_decision():
    candidates = _candidates(1)
    human = _sheet(candidates, ["message"], ["fam-1"], "michael")
    triage = [{"candidate_id": candidates[0]["candidate_id"], "resolution": "revise",
               "gold_class": "unknown", "gold_family_id": "fam-3", "notes": "thin fragment"}]
    final = single.apply_triage(human, triage)
    assert final[0]["gold_class"] == "unknown"
    assert final[0]["gold_family_id"] == "fam-3"
    assert final[0]["annotation_status"] == "human-revised-after-triage"
    assert final[0]["triage_notes"] == "thin fragment"


def test_unlabeled_items_are_unresolved_and_never_silently_dropped():
    candidates = _candidates(3)
    human = _sheet(candidates[:2], ["message"], ["fam-1"], "michael")
    merged = single.merge_records(candidates, single.apply_triage(human, []))
    assert len(merged["records"]) == 2
    assert merged["unresolved"] == [
        {"candidate_id": candidates[2]["candidate_id"], "reason": "missing human label"}]


def test_the_triage_csv_round_trips_through_the_rendered_template():
    candidates = _candidates(2)
    human = _sheet(candidates, ["message"], ["fam-1"], "michael")
    model = _sheet(candidates, ["unknown"], ["fam-1"], "model-rater")
    queue = single.triage_queue(human, model, candidates)
    template = single.render_triage_template(queue)
    assert template.splitlines()[0] == ",".join(single.TRIAGE_COLUMNS)
    filled = template.replace(",,,,", ",keep,,,")
    rows = single.read_triage_csv(filled)
    assert len(rows) == 2
    assert single.validate_triage(rows, single.triage_required_ids(queue)) == []


def test_the_whole_flow_over_the_committed_pilot_stamps_every_output():
    candidates = _candidates(20)
    classes = list(eligibility.SURFACE_CLASSES)
    human = _sheet(candidates, classes, ["fam-a", "fam-b", "fam-c"], "michael")
    model = _sheet(candidates, classes[1:] + classes[:1], ["fam-a", "fam-b"], "model-rater")

    report = single.human_versus_model_report(
        human, model, candidates, human_rater="michael", model_rater="model-rater",
        sample="pilot")
    queue = single.triage_queue(human, model, candidates)
    triage = [{"candidate_id": cid, "resolution": "keep", "gold_class": "",
               "gold_family_id": "", "notes": ""}
              for cid in sorted(single.triage_required_ids(queue))]
    assert single.validate_triage(triage, single.triage_required_ids(queue)) == []

    final = single.apply_triage(human, triage)
    merged = single.merge_records(candidates, final)
    assert merged["unresolved"] == []
    metrics = single.metrics(merged["records"], final, human_rater="michael",
                             model_rater="model-rater", sample="pilot")

    for payload in (report, metrics):
        assert payload["label"] == single.PROVENANCE_LABEL
        assert payload["provenance"]["mode"] == "single-human-rater"
        assert payload["provenance"]["gate_b_claimed"] is False
        single.assert_no_inter_annotator_claim(payload)
    assert metrics["records"] == 20
    assert metrics["triage_summary"]["labels_total"] == 20
    assert metrics["message_precision"]["denominator"] >= 0
    assert set(metrics["confusion_matrix"]) == set(eligibility.SURFACE_CLASSES)
