"""X9 acceptance tests for stable and diagnosable document families."""
from __future__ import annotations

from pipeline import config, document_families, site


COMMON = (
    "today our delegation requests immediate transparent action to protect every community "
    "and provide a complete public accounting of the agency response for residents across "
    "the state while preserving services and ensuring officials answer every pending question"
)


def _doc(doc_id: str, office: str, timestamp: str, suffix: str) -> dict:
    return {
        "id": doc_id,
        "text": f"Representative {office} writes that {COMMON} {suffix}",
        "published_at": timestamp,
        "member": {"bioguide": office, "party": "D"},
        "joint_group": None,
    }


def test_late_arrival_changes_revision_but_no_existing_family_id():
    documents = [
        _doc("B", "B", "2026-07-24T08:00:00Z", "without delay"),
        _doc("C", "C", "2026-07-24T09:00:00Z", "this week"),
    ]
    assert document_families.apply_families(documents) == 1
    family_id = documents[0]["document_family"]["family_id"]
    revision = documents[0]["document_family"]["family_revision"]
    assert family_id.startswith("njoint:")

    documents.append(_doc("A-late", "A", "2026-07-25T08:00:00Z", "for every resident"))
    assert document_families.apply_families(documents) == 1
    assert {row["document_family"]["family_id"] for row in documents} == {family_id}
    new_revision = documents[0]["document_family"]["family_revision"]
    assert new_revision != revision
    assert revision in documents[0]["document_family"]["previous_revisions"]


def test_candidate_window_is_wider_than_one_day_and_bounded_at_36_hours():
    near = [
        _doc("A", "A", "2026-07-24T23:00:00Z", "without delay"),
        _doc("B", "B", "2026-07-25T10:00:00Z", "this week"),
    ]
    far = [near[0], _doc("C", "C", "2026-07-26T12:00:00Z", "this month")]
    assert len(document_families.cluster_documents(near)) == 1
    assert document_families.cluster_documents(far) == []


def test_recall_harness_compares_minhash_with_exhaustive_pairs_at_target():
    documents = [
        _doc(f"D{index}", f"D{index}", f"2026-07-24T{8 + index:02d}:00:00Z", suffix)
        for index, suffix in enumerate(("without delay", "this week", "for every resident", "right now"))
    ]
    documents.append(_doc("late", "late", "2026-07-28T08:00:00Z", "outside the window"))
    report = document_families.recall_report(documents, max_documents=20)
    assert report["exhaustive_positive_pairs"] == 6
    assert report["recall"] == 1.0
    assert report["target"] == 0.995
    assert report["meets_target"] is True
    assert report["denominator"] == "exhaustive positive pairs in the bounded temporal subset"


def test_family_diagnostics_and_revision_pin_are_complete():
    family = document_families.cluster_documents([
        _doc("A", "A", "2026-07-24T08:00:00Z", "without delay"),
        _doc("B", "B", "2026-07-24T09:00:00Z", "this week"),
    ])[0]
    assert family["medoid_content_sha256"]
    assert set(family["member_similarities"]) == {"A", "B"}
    assert family["retrieval_path"] == "minhash-band then exact-jaccard"
    assert family["duplicate_class"] == "near_duplicate"
    assert family["versions"]["window_hours"] == config.DOCUMENT_FAMILY_WINDOW_HOURS
    assert family["family_revision"].startswith("dfrev:")


def test_public_method_states_the_family_support_unit_exactly():
    assert "One family is one support unit." in site.methodology_body()
