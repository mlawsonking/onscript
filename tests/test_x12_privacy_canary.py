"""X12 acceptance tests for name shapes, typed entities, and publication canaries."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline import privacy, privacy_canary, util


ROOT = Path(__file__).resolve().parents[1]


def test_review_name_shape_battery_quarantines_every_unresolved_person_shape():
    cases = {
        "plain": "Avery Stone addressed the committee",
        "middle_initial": "Avery J. Stone addressed the committee",
        "initials": "A. J. Stone addressed the committee",
        "hyphenated": "Avery Stone-River addressed the committee",
        "apostrophe": "Avery D'Arcy addressed the committee",
        "suffix": "Avery Stone Jr. addressed the committee",
        "particle": "Maria de Leon addressed the committee",
        "accented": "María León addressed the committee",
        "all_caps": "AVERY STONE addressed the committee",
    }
    for shape, text in cases.items():
        rows = privacy.person_spans(text, roster_map={})
        assert any(row["entity_type"] == "person.unresolved.quarantine" for row in rows), shape
        assert all(row["entity_version"] == "person-entities-v1" for row in rows)


def test_typed_hierarchy_separates_official_allowlisted_private_and_unresolved():
    roster = {"X1": {"name": "Ada Lovelace"}}
    official = privacy.person_spans(
        "Senator Ada Lovelace supports public records", roster_map=roster
    )
    unresolved = privacy.person_spans("Avery Stone supports public records", roster_map={})
    assert any(row["entity_type"] == "person.public.elected" for row in official)
    assert any(row["entity_type"] == "person.unresolved.quarantine" for row in unresolved)
    assert set(privacy.ENTITY_TYPES.values()) == {
        "person.private.admitted", "person.public.elected",
        "person.public.allowlisted", "person.unresolved.quarantine",
    }


def test_seeded_canary_failure_blocks_the_publish_callback_in_dry_run():
    calls = []
    try:
        privacy_canary.publication_rehearsal(
            lambda: calls.append("published"), seed_failure=True
        )
    except privacy_canary.PrivacyCanaryError:
        pass
    else:
        raise AssertionError("seeded canary failure did not stop publication")
    assert calls == []


def test_canary_telemetry_is_aggregate_and_contains_no_occurrences():
    with TemporaryDirectory() as td:
        path = Path(td) / "privacy-canary.json"
        result = privacy_canary.run(telemetry_path=path)
        assert util.read_json(path) == result
    assert result["passed"] is True
    assert result["checks_passed"] == result["checks_run"]
    assert result["occurrence_level_records"] == 0
    assert "names" not in result and "occurrences" not in result


def test_workflows_run_fail_closed_canaries_before_render_and_post():
    assemble = (ROOT / ".github/workflows/assemble.yml").read_text(encoding="utf-8")
    post = (ROOT / ".github/workflows/post.yml").read_text(encoding="utf-8")
    assert assemble.index("python -m pipeline.privacy_canary") < assemble.index("python pipeline/site.py")
    assert post.index("python -m pipeline.privacy_canary") < post.index("python pipeline/post_bluesky.py")
    assert "|| true" not in assemble[assemble.index("python -m pipeline.privacy_canary"):][:100]
    assert "|| true" not in post[post.index("python -m pipeline.privacy_canary"):][:100]
