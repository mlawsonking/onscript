"""Tests for the annotator packet generator."""
from pipeline import goldset_bundle as gb


def _statement(sid, party, day, text, title="A release", joint=None, url="https://x.gov/1"):
    return {
        "id": sid, "lane": 1, "member": {"bioguide": sid[:4], "party": party,
                                          "state": "CA", "chamber": "house"},
        "published_at": day, "title": title, "url": url, "text": text,
        "joint_group": joint,
    }


def test_neighbor_sentences_returns_before_containing_after():
    text = "First sentence here. The middle class families deserve better. A closing note."
    occ = text.index("The middle")
    before, sentence, after = gb._neighbor_sentences(text, occ)
    assert before == "First sentence here."
    assert "middle class families" in sentence
    assert after == "A closing note."


def test_build_item_masks_context_and_shows_office():
    anchor = _statement("sha256:aaa", "D", "2025-05-01",
                        "We fight for the middle class families of this state. That is our promise.",
                        title="On the middle class")
    candidate = {
        "candidate_id": "cand:1", "ngram": "the middle class families",
        "anchor_statement_id": "sha256:aaa", "day": "2025-05-01", "party": "D",
        "member_count": 1, "occurrence_start_char": anchor["text"].index("the middle"),
    }
    item = gb.build_item(candidate, {"sha256:aaa": anchor}, {})
    assert item["phrase"] == "the middle class families"
    assert "middle class families" in item["sentence"]
    assert item["office"] == "D-CA House"
    assert item["date"] == "2025-05-01"
    assert item["support"] == []  # member_count < 2


def test_support_set_dedups_by_family_and_caps():
    phrase = "protect social security now"
    text = "We will protect social security now and always."
    by_day = {"2025-06-01": [
        _statement("sha256:001", "D", "2025-06-01", text, joint="joint:letter-1"),
        _statement("sha256:002", "D", "2025-06-01", text, joint="joint:letter-1"),  # same family
        _statement("sha256:003", "D", "2025-06-01", text, joint=None),              # distinct
        _statement("sha256:004", "R", "2025-06-01", text, joint=None),              # wrong party
    ]}
    candidate = {"candidate_id": "cand:2", "ngram": phrase, "day": "2025-06-01",
                 "party": "D", "member_count": 3}
    rows = gb.support_set(candidate, by_day)
    assert len(rows) == 2  # one per family, republican excluded
    assert all("social security now" in row["sentence"] for row in rows)


def test_support_set_skipped_for_redacted_phrase():
    candidate = {"candidate_id": "cand:3", "ngram": "<private-individual-x> case",
                 "day": "2025-06-01", "party": "D", "member_count": 5, "phrase_redacted": True}
    assert gb.support_set(candidate, {}) == []


def test_annotator_order_is_deterministic_and_differs_by_annotator():
    candidates = [{"candidate_id": f"cand:{i}"} for i in range(20)]
    a1 = gb.annotator_order(candidates, "seed", "ann-a")
    a2 = gb.annotator_order(candidates, "seed", "ann-a")
    b1 = gb.annotator_order(candidates, "seed", "ann-b")
    assert [r["candidate_id"] for r in a1] == [r["candidate_id"] for r in a2]
    assert [r["candidate_id"] for r in a1] != [r["candidate_id"] for r in b1]
    # Same members, only order differs.
    assert {r["candidate_id"] for r in a1} == {r["candidate_id"] for r in b1}


def _sample_item():
    return {
        "candidate_id": "cand:1", "phrase": "the middle class families",
        "before": "Before text.", "sentence": "We defend the middle class families today.",
        "after": "After text.", "title": "A release", "office": "D-CA House",
        "date": "2025-05-01", "support": [],
    }


def test_render_html_is_self_contained_and_hides_machine_signals():
    html_page = gb.render_html([_sample_item()], annotator_id="ann-a",
                               sample="pilot", seed="s")
    assert html_page.startswith("<!doctype html>")
    # No external asset references.
    assert "http://" not in html_page and "https://" not in html_page
    assert "src=" not in html_page and "<link" not in html_page
    # No leaked machine signals.
    for banned in ("predicted_class", "priority", "impact_tags", "surge", "ranking", "seal_hash"):
        assert banned not in html_page
    assert "cand:1" in html_page
    assert "<mark>" in html_page  # phrase highlighted


def test_render_csv_has_answer_columns_and_row_per_item():
    csv_text = gb.render_csv([_sample_item(), {**_sample_item(), "candidate_id": "cand:2"}])
    lines = csv_text.strip().splitlines()
    assert lines[0].split(",")[0] == "candidate_id"
    assert "gold_class" in lines[0] and "gold_family_id" in lines[0]
    assert lines[1].startswith("cand:1,")
    assert lines[2].startswith("cand:2,")
    assert len(lines) == 3


def test_highlight_escapes_html_and_marks_phrase():
    out = gb._highlight("We back <b>the plan</b> and the plan works", "the plan")
    assert "&lt;b&gt;" in out           # escaped, not raw tag
    assert "<mark>the plan</mark>" in out
