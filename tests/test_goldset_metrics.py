"""Tests for gold-set intake, agreement, and confidence-interval metrics."""
from pipeline import goldset_metrics as gm


def test_read_answer_csv_coerces_types():
    text = (
        "candidate_id,gold_class,gold_family_id,phrase_complete,proposition_consistent,"
        "stance,claim_supported,notes\n"
        "cand:1,message,fam-1,true,yes,affirmative,1,looks clear\n"
        "cand:2,unknown,fam-2,false,no,negated,0,\n"
        ",,,,,,,\n"  # blank candidate_id skipped
    )
    rows = gm.read_answer_csv(text, "ann-a")
    assert len(rows) == 2
    assert rows[0]["annotator_id"] == "ann-a"
    assert rows[0]["phrase_complete"] is True
    assert rows[0]["claim_supported"] is True
    assert rows[0]["stance"] == "affirmative"
    assert rows[1]["phrase_complete"] is False
    assert rows[1]["stance"] == "negated"
    assert "notes" not in rows[1]


def test_validate_rows_flags_schema_violations():
    rows = [
        {"candidate_id": "cand:1", "annotator_id": "a", "gold_class": "message", "gold_family_id": "f"},
        {"candidate_id": "cand:2", "annotator_id": "a", "gold_class": "banana", "gold_family_id": "f"},
        {"candidate_id": "cand:3", "annotator_id": "a", "gold_class": "message", "gold_family_id": ""},
        {"candidate_id": "cand:4", "annotator_id": "a", "gold_class": "message",
         "gold_family_id": "f", "stance": "sideways"},
    ]
    errors = gm.validate_rows(rows)
    assert any("banana" in e for e in errors)
    assert any("cand:3" in e and "family" in e for e in errors)
    assert any("sideways" in e for e in errors)


def test_unknown_class_is_valid_after_schema_reconciliation():
    rows = [{"candidate_id": "c", "annotator_id": "a", "gold_class": "unknown", "gold_family_id": "f"}]
    assert gm.validate_rows(rows) == []


def test_cohens_kappa_perfect_and_chance():
    perfect = [("message", "message")] * 5 + [("unknown", "unknown")] * 5
    assert gm.cohens_kappa(perfect) == 1.0
    # Complete disagreement on a balanced two-class problem yields negative kappa.
    disagree = [("message", "unknown"), ("unknown", "message")] * 5
    assert gm.cohens_kappa(disagree) < 0


def test_krippendorff_alpha_perfect_agreement():
    perfect = [("a", "a"), ("b", "b"), ("a", "a"), ("b", "b")]
    assert gm.krippendorff_alpha(perfect) == 1.0


def test_wilson_interval_brackets_estimate():
    low, high = gm.wilson_interval(8, 10)
    assert 0.0 <= low <= 0.8 <= high <= 1.0
    assert gm.wilson_interval(0, 0) is None


def test_agreement_report_reports_gates():
    candidates = [
        {"candidate_id": "c1", "day": "2025-05-01", "party": "D"},
        {"candidate_id": "c2", "day": "2025-05-01", "party": "D"},
    ]
    a = [
        {"candidate_id": "c1", "annotator_id": "a", "gold_class": "message", "gold_family_id": "f1"},
        {"candidate_id": "c2", "annotator_id": "a", "gold_class": "unknown", "gold_family_id": "f2"},
    ]
    b = [
        {"candidate_id": "c1", "annotator_id": "b", "gold_class": "message", "gold_family_id": "f1"},
        {"candidate_id": "c2", "annotator_id": "b", "gold_class": "unknown", "gold_family_id": "f9"},
    ]
    report = gm.agreement_report(a, b, candidates)
    assert report["dual_annotated_items"] == 2
    assert report["tasks"]["surface_class"]["observed_agreement"] == 1.0
    assert report["pilot_gates"]["values"]["overall_agreement"] == 1.0
    assert report["pilot_gates"]["pass"]["message_vs_nonmessage_agreement"] is True


def test_adjudication_queue_finds_disagreements():
    candidates = [{"candidate_id": "c1"}, {"candidate_id": "c2"}, {"candidate_id": "c3"}]
    a = [
        {"candidate_id": "c1", "annotator_id": "a", "gold_class": "message", "gold_family_id": "f"},
        {"candidate_id": "c2", "annotator_id": "a", "gold_class": "message", "gold_family_id": "f"},
        {"candidate_id": "c3", "annotator_id": "a", "gold_class": "message", "gold_family_id": "f"},
    ]
    b = [
        {"candidate_id": "c1", "annotator_id": "b", "gold_class": "message", "gold_family_id": "f"},
        {"candidate_id": "c2", "annotator_id": "b", "gold_class": "unknown", "gold_family_id": "f"},
        {"candidate_id": "c3", "annotator_id": "b", "gold_class": "message", "gold_family_id": "g"},
    ]
    queue = gm.adjudication_queue(a, b, candidates)
    reasons = {row["candidate_id"]: row["reason"] for row in queue}
    assert "c1" not in reasons          # agreement, not queued
    assert reasons["c2"] == "class"
    assert reasons["c3"] == "family"


def test_metrics_with_intervals_reports_num_denom_ci():
    records = [
        {"party": "D", "day": "2025-05-01", "predicted_class": "message", "gold_class": "message",
         "predicted_family_id": "p1", "gold_family_id": "g1"},
        {"party": "D", "day": "2025-05-01", "predicted_class": "message", "gold_class": "message",
         "predicted_family_id": "p1", "gold_family_id": "g1"},
        {"party": "R", "day": "2025-05-02", "predicted_class": "message", "gold_class": "unknown",
         "predicted_family_id": "p2", "gold_family_id": "g2"},
        {"party": "R", "day": "2025-05-02", "predicted_class": "unknown", "gold_class": "unknown",
         "predicted_family_id": "p3", "gold_family_id": "g3"},
    ]
    metrics = gm.metrics_with_intervals(records)
    message = metrics["message_precision"]
    # 2 true message of 3 predicted message.
    assert message["numerator"] == 2 and message["denominator"] == 3
    assert message["ci95"][0] <= message["estimate"] <= message["ci95"][1]
    # Family pairwise: the two D records share predicted and gold family -> one true positive pair.
    assert metrics["family_pairwise"]["precision"]["numerator"] == 1
    gap = metrics["party_error_gap"]
    assert gap["D"]["denominator"] == 2 and gap["R"]["denominator"] == 2
    assert gap["gap_ci95"] is not None


def test_merge_records_requires_decision_for_disagreement():
    candidates = [{"candidate_id": "c1", "party": "D", "day": "2025-05-01",
                   "predicted_class": "message", "predicted_family_id": "p1"}]
    a = [{"candidate_id": "c1", "annotator_id": "a", "gold_class": "message", "gold_family_id": "f"}]
    b = [{"candidate_id": "c1", "annotator_id": "b", "gold_class": "unknown", "gold_family_id": "f"}]
    merged = gm.merge_records(candidates, a, b, [])
    assert merged["unresolved"]
    decided = gm.merge_records(candidates, a, b, [
        {"candidate_id": "c1", "adjudicator_id": "adj", "gold_class": "message", "gold_family_id": "f"}])
    assert not decided["unresolved"]
    assert decided["records"][0]["annotation_status"] == "adjudicated"
