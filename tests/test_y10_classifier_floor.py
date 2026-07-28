"""Y10 acceptance: classifier floor hardening (R-36.7).

On a public surface a phrase with no family evidence classifies unknown instead of falling
through to the message floor. The generic survivors are a fixture set documenting current
behavior for the gold set to adjudicate, registered for public-surface sampling, not a
hand-tuned blocklist. The stricter rule stays dark until the gold set validates it.
"""
from __future__ import annotations

import inspect
import json

from pipeline import config, eligibility
from pipeline import goldset_sample as gs

SURVIVORS = ("billions of dollars", "communities across the country")


def test_family_evidence_absent_public_claims_classify_unknown():
    for ngram in SURVIVORS:
        strict = eligibility.classify_phrase(ngram, family_count=None, require_family_evidence=True)
        assert strict["surface_class"] == "unknown"
        assert strict["classifier"]["rule"] == "family-evidence-absent"


def test_the_message_floor_is_unchanged_by_default():
    for ngram in SURVIVORS:
        assert eligibility.classify_phrase(ngram, family_count=None)["surface_class"] == "message"
    # a present family_count below quorum still reads family-quorum-unmet, not evidence-absent
    below = eligibility.classify_phrase("protect medicare now", family_count=2)
    assert below["classifier"]["rule"] == "family-quorum-unmet"


def test_the_statement_count_fallback_survives_only_for_legacy_fixtures():
    claim = {"label": "x", "statements": ["a", "b", "c"]}
    assert eligibility._family_count(claim, legacy=True) == 3
    assert eligibility._family_count(claim, legacy=False) is None
    # real family evidence is read on either path
    assert eligibility._family_count({"counts": {"families": 4}}, legacy=False) == 4


def test_classify_claim_strict_drops_a_statements_only_claim():
    claim = {"label": "communities across the country", "statements": ["a", "b", "c"], "day": "2026-07-24"}
    assert eligibility.classify_claim(claim)["surface_class"] == "message"
    strict = eligibility.classify_claim(claim, require_family_evidence=True)
    assert strict["surface_class"] == "unknown"
    assert strict["classifier"]["rule"] == "family-evidence-absent"


def test_the_generic_survivor_fixture_documents_current_behavior():
    data = json.loads(
        (config.REPO_ROOT / "evaluation" / "goldset" / "generic_survivors.json").read_text(encoding="utf-8"))
    rows = data["survivors"]
    assert rows
    for row in rows:
        live = eligibility.classify_phrase(row["ngram"], family_count=None)
        assert live["surface_class"] == row["documented_class"] == "message"
        assert live["classifier"]["rule"] == row["documented_rule"]
        strict = eligibility.classify_phrase(row["ngram"], family_count=None, require_family_evidence=True)
        assert strict["surface_class"] == row["strict_class"] == "unknown"


def test_the_fixture_is_not_a_blocklist_the_classifier_never_reads_it():
    source = inspect.getsource(eligibility)
    assert "generic_survivors" not in source
    for ngram in SURVIVORS:
        assert ngram not in source


def test_the_survivors_are_registered_for_public_surface_sampling():
    survivors = gs.survivor_phrases()
    for ngram in SURVIVORS:
        assert ngram in survivors


def _universe_with_survivor() -> list[dict]:
    universe = []
    sizes = {"message": 300, "procedural": 160, "unknown": 90, "nomenclature": 30}
    counter = 0
    for cls, total in sizes.items():
        for index in range(total):
            counter += 1
            universe.append({
                "candidate_id": f"cand:{counter:07d}",
                "ngram": f"{cls} phrase {index}", "n": 4,
                "day": "2025-05-01" if index % 3 else "2026-05-01",
                "year": "2025" if index % 3 else "2026",
                "party": "D" if index % 2 else "R", "lane": 1,
                "member_count": (index % 5) + 1, "member_headcount": (index % 5) + 1,
                "family_evidence_count": (index % 5) + 1,
                "predicted_class": cls, "classifier_rule": "synthetic",
            })
    universe.append({
        "candidate_id": "cand:survivor", "ngram": "billions of dollars", "n": 3,
        "day": "2026-05-01", "year": "2026", "party": "D", "lane": 1,
        "member_count": 4, "member_headcount": 4, "family_evidence_count": 4,
        "predicted_class": "message", "classifier_rule": "affirmative-deterministic-floor",
    })
    return universe


def test_a_public_tagged_survivor_is_drawn_into_the_pilot():
    universe = _universe_with_survivor()
    gs.tag_impact(universe, public_phrases=gs.survivor_phrases())
    survivor = next(row for row in universe if row["candidate_id"] == "cand:survivor")
    assert "public_surface" in survivor["impact_tags"]
    manifest = gs.seal(universe, seed="onscript-goldset-v1", pilot_size=200, full_size=400,
                       split_boundaries={"train_end": "2025-12-31", "validation_end": "2026-03-31"})
    drawn = {row["candidate_id"] for row in manifest["pilot"] + manifest["full"]}
    assert "cand:survivor" in drawn
