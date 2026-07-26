"""W7 acceptance tests for deterministic document families."""
from pipeline import config, document_families, normalize


def _record(url: str, text: str, office: str) -> dict:
    return {
        "url": url,
        "text": text,
        "title": "Family fixture",
        "date": "2026-07-24",
        "member": {
            "bioguide_id": office,
            "party": "Democrat",
            "state": "CA",
            "chamber": "House",
        },
    }


def _document(doc_id: str, text: str) -> dict:
    return {
        "id": doc_id,
        "text": text,
        "published_at": "2026-07-24",
        "member": {"bioguide": doc_id, "party": "D"},
        "joint_group": None,
    }


def test_one_joint_release_many_offices_is_one_family():
    body = "We jointly request a complete public accounting and prompt action on this urgent matter."
    rows = normalize.normalize_records(
        [_record(f"https://example.test/{office}", body, office) for office in "ABCDE"],
        run_id="w7-fixture",
    )
    family_ids = {row["document_family"]["family_id"] for row in rows}
    assert len(family_ids) == 1
    assert {row["document_family"]["publication_count"] for row in rows} == {5}


def test_near_duplicates_with_local_edits_cluster():
    common = (
        "today our delegation requests immediate transparent action to protect every community "
        "and provide a complete public accounting of the agency response for residents across "
        "the state while preserving services and ensuring officials answer every pending question"
    )
    documents = [
        _document("A", "Representative Alpha writes that " + common + " without delay"),
        _document("B", "Representative Beta writes that " + common + " this week"),
    ]
    families = document_families.cluster_documents(documents)
    assert len(families) == 1
    assert families[0]["statement_ids"] == ["A", "B"]
    assert families[0]["medoid_statement_id"] in {"A", "B"}


def test_similarity_chain_does_not_form_one_transitive_family():
    base = [f"token{index}" for index in range(1, 81)]
    a = " ".join(base[:60])
    b = " ".join(base[:70])
    c = " ".join(base[10:80])
    documents = [_document("A", a), _document("B", b), _document("C", c)]
    sa, sb, sc = [document_families.shingles(row["text"]) for row in documents]
    assert document_families.exact_similarity(sa, sb) >= config.DOCUMENT_FAMILY_JACCARD
    assert document_families.exact_similarity(sb, sc) >= config.DOCUMENT_FAMILY_JACCARD
    assert document_families.exact_similarity(sa, sc) < config.DOCUMENT_FAMILY_JACCARD
    families = document_families.cluster_documents(documents)
    assert not any(set(row["statement_ids"]) == {"A", "B", "C"} for row in families)
    assert any(set(row["statement_ids"]) == {"A", "B"} for row in families)


def test_thresholds_are_party_blind_and_marked_provisional():
    source = open(config.__file__, encoding="utf-8").read()
    assert "These thresholds are PROVISIONAL" in source
    assert not hasattr(config, "DOCUMENT_FAMILY_JACCARD_D")
    assert not hasattr(config, "DOCUMENT_FAMILY_JACCARD_R")
