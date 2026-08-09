"""N1 acceptance: the pilot re-seal that admits the Y10 generic survivors.

The seal is only auditable if the verifier reconstructs the same frame the builder sealed, so
the public-impact set is one function both paths call. The committed kit is validated as a
pinned record: internally consistent, disjoint, anchored, and carrying the supersession of the
kit it replaced. Nothing here rebuilds the frame from the multi-gigabyte ledger; that is what
``scripts/goldset_seal.py verify`` is for.
"""
from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path

from pipeline import config, goldset_sample


GOLDSET = Path(config.REPO_ROOT) / "evaluation" / "goldset"
SEAL_SCRIPT = Path(config.REPO_ROOT) / "scripts" / "goldset_seal.py"
SUPERSEDED_SEAL = "2c349e56b37e326950596b9acb3780b57c4cc6b37985a7709f219b3a25880ec1"


def _seal_module():
    spec = importlib.util.spec_from_file_location("goldset_seal_script", SEAL_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(name: str) -> dict:
    return json.loads((GOLDSET / name).read_text(encoding="utf-8"))


def test_build_and_verify_read_one_public_impact_set():
    """Both paths reach the impact set through ``public_phrase_set`` and nothing else.

    The seal is auditable only if the verifier reconstructs the frame the builder sealed, so
    neither path may carry its own copy of the union. ``verify`` now reaches it through
    ``rebuild_seal``, which is where the impact input became a parameter so a rebuild can be
    pinned to the tree the sample was drawn from.
    """
    module = _seal_module()
    assert "public_phrase_set(" in inspect.getsource(module.build)
    assert "public_phrase_set(" in inspect.getsource(module.rebuild_seal)
    assert "rebuild_seal(" in inspect.getsource(module.verify)
    # One definition and exactly two call sites: no third construction of the set.
    assert inspect.getsource(module).count("public_phrase_set(") == 3


def test_verify_can_pin_its_impact_input_to_the_sealing_commit():
    """The impact set is built from data/derived/days, a tree that grows with production.

    Rebuilding against the live tree reports a mismatch for a sample that never moved, which
    is the docs/37 rule 3 shape, so verify accepts the tree the seal was drawn from. Behavior
    with no ref is unchanged.
    """
    module = _seal_module()
    source = inspect.getsource(module.verify)
    assert "_day_artifacts_as_of(as_of) if as_of else _day_artifacts()" in source
    signature = inspect.signature(module.verify)
    assert list(signature.parameters) == ["as_of"]
    assert signature.parameters["as_of"].default is None


def test_the_public_impact_set_admits_the_generic_survivors():
    module = _seal_module()
    days = [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((config.DERIVED / "days").glob("*.json"))]
    public = module.public_phrase_set(days)
    survivors = goldset_sample.survivor_phrases()
    assert survivors
    assert survivors <= public


def test_the_manifest_records_the_kit_it_supersedes():
    manifest = _load("MANIFEST.json")
    superseded = manifest.get("supersedes") or {}
    assert superseded.get("seal_hash") == SUPERSEDED_SEAL
    assert manifest["seal_hash"] != SUPERSEDED_SEAL
    assert manifest["method_version"] == goldset_sample.SAMPLE_METHOD_VERSION


def test_the_sealed_kit_is_internally_consistent():
    manifest = _load("MANIFEST.json")
    pilot, full = _load("pilot.sample.json"), _load("full.sample.json")
    for sample in (pilot, full):
        assert sample["seal_hash"] == manifest["seal_hash"]
        assert sample["universe_fingerprint"] == manifest["universe_fingerprint"]
        assert sample["split_boundaries"] == manifest["split_boundaries"]
        assert sample["size"] == len(sample["candidates"])
    assert pilot["size"] == manifest["pilot_size"] == 200
    assert full["size"] == manifest["full_size"] == 1400

    pilot_ids = {row["candidate_id"] for row in pilot["candidates"]}
    full_ids = {row["candidate_id"] for row in full["candidates"]}
    assert len(pilot_ids) == pilot["size"] and len(full_ids) == full["size"]
    assert not pilot_ids & full_ids


def test_every_sealed_candidate_is_anchored_and_split():
    manifest = _load("MANIFEST.json")
    rows = _load("pilot.sample.json")["candidates"] + _load("full.sample.json")["candidates"]
    assert manifest["unresolved_anchors"] == 0
    assert all(row["anchor_resolved"] for row in rows)
    assert all(row["anchor_statement_id"] for row in rows)
    assert all(row["split"] in ("train", "validation", "test") for row in rows)


def test_every_survivor_in_the_frame_carries_the_public_surface_tag():
    survivors = goldset_sample.survivor_phrases()
    rows = _load("pilot.sample.json")["candidates"] + _load("full.sample.json")["candidates"]
    drawn = [row for row in rows if row["ngram"] in survivors]
    assert drawn, "the re-seal drew no generic survivor into the frame"
    for row in drawn:
        assert "public_surface" in row["impact_tags"], row["ngram"]
        assert row["priority"] >= goldset_sample.IMPACT_WEIGHTS["public_surface"]


def test_the_redacted_phrases_never_carry_an_admitted_form():
    from pipeline import privacy

    rows = _load("pilot.sample.json")["candidates"] + _load("full.sample.json")["candidates"]
    redacted = [row for row in rows if row.get("phrase_redacted")]
    assert redacted, "the sealed kit records no redacted phrase; the floor is untested here"
    assert not any(privacy.contains_admitted_form(row["ngram"]) for row in rows)
