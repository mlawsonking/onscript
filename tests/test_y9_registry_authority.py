"""Y9 acceptance: registry-versus-authority invariants (R-36.1).

Every central registry is tested against its live owning authority, and the registry
mutation harness reports each invariant load-bearing so removal or a stale copy is caught.
"""
from __future__ import annotations

import importlib

from pipeline import (config, corrections, eligibility, instrument_fingerprint as fp,
                      public_strings, site, status_exports, util)
from tests.registry_mutations import REGISTRY_INVARIANTS, run_registry_mutations


def test_every_method_version_entry_matches_its_live_owner():
    versions = fp.method_versions()
    for key, module, attr in fp.METHOD_VERSION_PROVIDERS:
        owner = getattr(importlib.import_module(f"pipeline.{module}"), attr)
        assert versions[key] == owner, key


def test_every_schema_version_entry_matches_its_live_owner():
    schemas = fp.schema_versions()
    for key, module, attr in fp.SCHEMA_VERSION_PROVIDERS:
        owner = getattr(importlib.import_module(f"pipeline.{module}"), attr)
        assert schemas[key] == owner, key


def test_every_registry_entry_has_an_owning_authority():
    # No method or schema version is a registry-local literal with no owner.
    registry_keys = ({key for key, _m, _a in fp.METHOD_VERSION_PROVIDERS}
                     | {key for key, _m, _a in fp.SCHEMA_VERSION_PROVIDERS})
    assert set(fp.method_versions()) <= registry_keys
    assert set(fp.schema_versions()) == {key for key, _m, _a in fp.SCHEMA_VERSION_PROVIDERS}


def test_a_bumped_method_authority_changes_the_published_fingerprint():
    # A one-line bump of any live authority moves the fingerprint with no registry edit.
    from pipeline import surges
    base = fp.build()["sha256"]
    original = surges.METHOD_VERSION
    try:
        surges.METHOD_VERSION = original + "-probe"
        assert fp.build()["sha256"] != base
    finally:
        surges.METHOD_VERSION = original
    assert fp.build()["sha256"] == base


def test_feature_flags_have_no_second_copy():
    # feature_on reads config.FEATURES directly, so a flag has one authority, not a drifting copy.
    name = next(iter(config.FEATURES))
    original = config.FEATURES[name]
    try:
        config.FEATURES[name] = not original
        assert config.feature_on(name) == (not original)
    finally:
        config.FEATURES[name] = original


def test_public_strings_are_read_live_by_renderers():
    day_data = util.read_json(config.DERIVED / "days" / "2026-06-30.json", {})
    saved = public_strings.LEXICAL_TABLE_DISCLAIMER
    try:
        public_strings.LEXICAL_TABLE_DISCLAIMER = "PROBE-LEXICAL-DISCLAIMER-ZZZ"
        body = site.day_view_body("2026-06-30", day_data, set(), 1)
        assert "PROBE-LEXICAL-DISCLAIMER-ZZZ" in body
    finally:
        public_strings.LEXICAL_TABLE_DISCLAIMER = saved


def test_a_resolved_posting_state_is_a_member_of_the_posting_registry():
    for post in ({"posting_enabled": False}, {"atomic_hold": True},
                 {"results": [{"posted": True}, {"posted": True}]}):
        assert status_exports._posting_state(post) in status_exports.POSTING_STATES


def test_the_api_field_emitters_match_the_documented_contract():
    status = {"generated_at": "2026-07-27T12:00:00Z"}
    exports = status_exports.experimental_exports(status, [], {"by_peak": []}, [])
    import json
    for name, endpoint in status_exports.RESOURCE_ENDPOINTS.items():
        if name == "schema":
            continue
        envelope = json.loads(exports[endpoint])
        assert envelope["payload_fields"] == list(status_exports.RESOURCE_FIELDS[name])
        assert sorted(envelope["payload"]) == sorted(envelope["payload_fields"])


def test_the_correction_checkpoint_binds_to_the_ledger():
    rows = corrections.load()
    raised = False
    try:
        corrections.validate(rows[:-1], expected_count=len(rows))
    except ValueError as error:
        raised = "corrections count changed" in str(error)
    assert raised, "a checkpoint that disagrees with the ledger must fail closed"


def test_the_registry_mutation_harness_reports_every_invariant_load_bearing():
    report = run_registry_mutations()
    assert len(report) == len(REGISTRY_INVARIANTS)
    assert all(row["load_bearing"] for row in report)
    names = {row["invariant"] for row in report}
    # every method and schema version provider is covered
    for key, _module, _attr in fp.METHOD_VERSION_PROVIDERS:
        assert f"method_version:{key}" in names
    for key, _module, _attr in fp.SCHEMA_VERSION_PROVIDERS:
        assert f"schema_version:{key}" in names
    assert {"api_version", "canary_version", "entity_hierarchy_version"} <= names
