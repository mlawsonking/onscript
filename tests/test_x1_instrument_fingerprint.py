"""X1 acceptance tests for complete instrument identity."""
from __future__ import annotations

import copy

from pipeline import config, instrument_fingerprint, status_exports, util


def test_every_live_parameter_moves_the_authoritative_fingerprint():
    base = instrument_fingerprint.build()
    for name, value in instrument_fingerprint.live_thresholds().items():
        changed = value + 1 if isinstance(value, (int, float)) else f"{value}-changed"
        candidate = instrument_fingerprint.build(threshold_overrides={name: changed})
        assert candidate["sha256"] != base["sha256"], name


def test_dead_legacy_parameter_does_not_move_the_authoritative_fingerprint():
    base = instrument_fingerprint.build()
    original = config.NEAR_JOINT_JACCARD
    try:
        config.NEAR_JOINT_JACCARD = original + 0.01
        changed = instrument_fingerprint.build()
    finally:
        config.NEAR_JOINT_JACCARD = original
    assert changed["sha256"] == base["sha256"]
    assert changed["thresholds_sha"] != base["thresholds_sha"]


def test_two_clean_builds_at_one_commit_agree():
    assert instrument_fingerprint.build() == instrument_fingerprint.build()


def test_real_committed_day_and_api_envelope_accept_the_same_fingerprint():
    path = config.DERIVED / "days" / "2026-07-24.json"
    committed = util.read_json(path, {})
    assert committed.get("day") == "2026-07-24"
    fingerprint = instrument_fingerprint.build()
    stamped = instrument_fingerprint.stamp(copy.deepcopy(committed), fingerprint)
    wrapped = status_exports.envelope(stamped, "2026-07-25T00:00:00Z")
    assert stamped["instrument_fingerprint"] == fingerprint
    assert wrapped["instrument_fingerprint"] == fingerprint
    assert status_exports.verify_envelope(wrapped)


def test_fingerprint_carries_required_inspectable_components_and_compatibility_hash():
    value = instrument_fingerprint.build()
    expected = {"code_tree", "schema_versions", "method_versions", "live_thresholds",
                "prompts", "privacy_forms", "nomenclature_index"}
    assert set(value["component_hashes"]) == expected
    assert len(value["sha256"]) == 64
    assert len(value["thresholds_sha"]) == 64
