"""Tests for the deterministic gold-set candidate universe and sealed sampling.

These exercise the sampler logic on small synthetic inputs so the suite stays fast. The
full-corpus seal is rebuilt and checked out of band by ``scripts/goldset_seal.py verify``.
"""
from collections import Counter

from pipeline import goldset_sample as gs


def _synthetic_ledger():
    return {
        "the middle class families": {
            "ngram": "the middle class families", "n": 4,
            "daily": {
                "2024-12-01": {"D": 9, "members_D": [f"D{i}" for i in range(9)]},  # pre-epoch
                "2025-02-10": {"D": 5, "members_D": [f"D{i}" for i in range(5)]},
                "2025-02-20": {"D": 7, "members_D": [f"D{i}" for i in range(7)]},
                "2025-03-05": {"R": 3, "members_R": ["R1", "R2", "R3"]},
            },
        },
        "on ways and means": {
            "ngram": "on ways and means", "n": 4,
            "daily": {"2025-04-01": {"D": 4, "members_D": ["D1", "D2", "D3", "D4"]}},
        },
        "was born in scranton": {
            "ngram": "was born in scranton", "n": 4,
            "daily": {"2026-05-01": {"D": 2, "members_D": ["D1", "D2"]}},
        },
    }


def test_build_universe_selects_peak_public_day_per_party():
    universe = gs.build_universe(_synthetic_ledger(), epoch="2025-01-03")
    by_phrase = {(row["ngram"], row["party"]): row for row in universe}
    # The Democratic peak is the 7-unit day, not the pre-epoch 9-unit day.
    demo = by_phrase[("the middle class families", "D")]
    assert demo["day"] == "2025-02-20"
    assert demo["member_count"] == 7
    # Republicans carried the same phrase separately on their own day.
    assert ("the middle class families", "R") in by_phrase


def test_epoch_gate_excludes_pre_epoch_occurrences():
    ledger = {"only pre epoch phrase": {
        "ngram": "only pre epoch phrase", "n": 4,
        "daily": {"2024-11-01": {"D": 8, "members_D": [f"D{i}" for i in range(8)]}},
    }}
    assert gs.build_universe(ledger, epoch="2025-01-03") == []


def test_candidate_id_is_stable_and_unique():
    universe = gs.build_universe(_synthetic_ledger(), epoch="2025-01-03")
    ids = [row["candidate_id"] for row in universe]
    assert len(ids) == len(set(ids))
    assert all(cid.startswith("cand:") for cid in ids)
    # Deterministic across runs.
    again = gs.build_universe(_synthetic_ledger(), epoch="2025-01-03")
    assert [row["candidate_id"] for row in again] == ids


def _big_universe():
    """A synthetic frame with every class and both parties across two years."""
    universe = []
    sizes = {"message": 300, "procedural": 160, "unknown": 90,
             "nomenclature": 30, "biographical": 6, "private": 3}
    counter = 0
    for cls, total in sizes.items():
        for index in range(total):
            counter += 1
            party = "D" if index % 2 else "R"
            year = "2025" if index % 3 else "2026"
            universe.append({
                "candidate_id": f"cand:{counter:07d}",
                "ngram": f"{cls} phrase {index}", "n": 4,
                "day": f"{year}-05-01", "year": year, "party": party, "lane": 1,
                "member_count": (index % 5) + 1, "member_headcount": (index % 5) + 1,
                "family_evidence_count": (index % 5) + 1,
                "predicted_class": cls, "classifier_rule": "synthetic",
            })
    gs.tag_impact(universe, public_phrases=set())
    return universe


def test_seal_hits_exact_pilot_and_full_sizes_disjoint():
    universe = _big_universe()
    manifest = gs.seal(universe, seed="s", pilot_size=200, full_size=380,
                       split_boundaries={"train_end": "2025-12-31", "validation_end": "2026-03-31"})
    assert manifest["pilot_size"] == 200
    assert manifest["full_size"] == 380
    pilot = {row["candidate_id"] for row in manifest["pilot"]}
    full = {row["candidate_id"] for row in manifest["full"]}
    assert pilot.isdisjoint(full)
    assert len(pilot) == 200 and len(full) == 380


def test_seal_is_reproducible():
    universe = _big_universe()
    boundaries = {"train_end": "2025-12-31", "validation_end": "2026-03-31"}
    first = gs.seal(universe, seed="s", pilot_size=200, full_size=380, split_boundaries=boundaries)
    second = gs.seal(universe, seed="s", pilot_size=200, full_size=380, split_boundaries=boundaries)
    assert first["seal_hash"] == second["seal_hash"]
    assert [r["candidate_id"] for r in first["pilot"]] == [r["candidate_id"] for r in second["pilot"]]


def test_seal_hash_changes_when_frame_changes():
    universe = _big_universe()
    boundaries = {"train_end": "2025-12-31", "validation_end": "2026-03-31"}
    base = gs.seal(universe, seed="s", pilot_size=200, full_size=380, split_boundaries=boundaries)
    mutated = [dict(row) for row in universe]
    mutated[0]["predicted_class"] = "unknown"
    gs.tag_impact(mutated, public_phrases=set())
    changed = gs.seal(mutated, seed="s", pilot_size=200, full_size=380, split_boundaries=boundaries)
    assert base["universe_fingerprint"] != changed["universe_fingerprint"]
    assert base["seal_hash"] != changed["seal_hash"]


def test_seed_changes_selection():
    universe = _big_universe()
    boundaries = {"train_end": "2025-12-31", "validation_end": "2026-03-31"}
    one = gs.seal(universe, seed="alpha", pilot_size=200, full_size=380, split_boundaries=boundaries)
    two = gs.seal(universe, seed="omega", pilot_size=200, full_size=380, split_boundaries=boundaries)
    selected_one = {r["candidate_id"] for r in one["pilot"] + one["full"]}
    selected_two = {r["candidate_id"] for r in two["pilot"] + two["full"]}
    assert selected_one != selected_two


def test_rare_classes_survive_sampling():
    universe = _big_universe()
    manifest = gs.seal(universe, seed="s", pilot_size=200, full_size=380,
                       split_boundaries={"train_end": "2025-12-31", "validation_end": "2026-03-31"})
    classes = Counter(row["predicted_class"] for row in manifest["pilot"] + manifest["full"])
    # All 3 private and all 6 biographical are drawn because of the per-stratum floor.
    assert classes["private"] == 3
    assert classes["biographical"] == 6


def test_public_impact_is_oversampled():
    universe = _big_universe()
    # Mark ten message phrases as public-surface; they must all be drawn.
    public = {row["ngram"] for row in universe if row["predicted_class"] == "message"}
    public = set(sorted(public)[:10])
    gs.tag_impact(universe, public_phrases=public)
    manifest = gs.seal(universe, seed="s", pilot_size=200, full_size=380,
                       split_boundaries={"train_end": "2025-12-31", "validation_end": "2026-03-31"})
    drawn = {row["ngram"] for row in manifest["pilot"] + manifest["full"]}
    assert public.issubset(drawn)


def test_split_assignment_is_date_based():
    universe = _big_universe()
    manifest = gs.seal(universe, seed="s", pilot_size=200, full_size=380,
                       split_boundaries={"train_end": "2025-12-31", "validation_end": "2026-03-31"})
    for row in manifest["pilot"] + manifest["full"]:
        if row["day"] <= "2025-12-31":
            assert row["split"] == "train"
        else:
            assert row["split"] == "test"


def test_tag_impact_flags_boundary_and_family_collapse():
    universe = [
        {"candidate_id": "cand:1", "ngram": "a", "n": 4, "day": "2025-05-01", "year": "2025",
         "party": "D", "lane": 1, "member_count": 3, "member_headcount": 8,
         "family_evidence_count": 3, "predicted_class": "message", "classifier_rule": "x"},
    ]
    gs.tag_impact(universe, public_phrases=set())
    tags = set(universe[0]["impact_tags"])
    assert "boundary_quorum" in tags   # member_count in {2,3}
    assert "family_collapse" in tags   # headcount 8 > 3 units


def test_redact_for_publish_routes_every_phrase_through_privacy():
    # Patch the hardened label path so no real admitted form is embedded in this test.
    original = gs.privacy.redact

    def fake_redact(text):
        if text == "an admitted private form":
            return ("<private-individual-x> form", 1)
        return (text, 0)

    gs.privacy.redact = fake_redact
    try:
        rows = [
            {"candidate_id": "cand:1", "ngram": "the middle class families"},
            {"candidate_id": "cand:2", "ngram": "an admitted private form"},
        ]
        out = gs.redact_for_publish(rows)
        assert out[0]["ngram"] == "the middle class families"
        assert "phrase_redacted" not in out[0]
        assert out[1]["ngram"] == "<private-individual-x> form"
        assert out[1]["phrase_redacted"] is True
    finally:
        gs.privacy.redact = original


def test_day_surface_phrases_reads_dict_and_list_shapes():
    days = [{
        "talking_points": {
            "D": [{"label": "after the supreme court", "member_count": 53}],
            "R": [{"label": "the supreme court's decision"}],
        },
        "top_synchronized": [{"ngram": "born in the united states"}],
        "discipline": {"D": {"index": 0.73}, "R": {"index": 0.75}},
    }]
    phrases = gs._day_surface_phrases(days)
    assert "after the supreme court" in phrases
    assert "the supreme court's decision" in phrases
    assert "born in the united states" in phrases


def test_anchor_and_contextualize_locates_the_sentence():
    statements_by_day = {"2025-05-01": [{
        "id": "sha256:aaa", "lane": 1,
        "member": {"bioguide": "D1", "party": "D"},
        "published_at": "2025-05-01",
        "title": "A statement", "url": "https://example.gov/1",
        "text": "We must protect the middle class families across this country. That is the goal.",
    }]}
    rows = [{"candidate_id": "cand:1", "ngram": "the middle class families",
             "day": "2025-05-01", "party": "D", "predicted_class": "message"}]
    anchored = gs.anchor_and_contextualize(rows, statements_by_day)
    row = anchored[0]
    assert row["anchor_resolved"] is True
    assert row["anchor_statement_id"] == "sha256:aaa"
    assert row["predicted_family_id"]
    assert row["occurrence_start_char"] is not None
