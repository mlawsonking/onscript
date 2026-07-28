"""Y1 acceptance: fingerprint integrity (R-36.2).

The fingerprint reads its method and schema versions from the owning modules,
identifies code by a measurement-tree content hash rather than repository HEAD,
and is stamped once at assembly so posts and exports inherit the same bytes.
"""
from __future__ import annotations

import re
from pathlib import Path

from pipeline import (config, contracts, corrections, denominators, distill,
                      document_families, eligibility, instrument_fingerprint as fp,
                      participation, shadow_replay, status_exports, surges, util)


_METHOD_SYMBOL = re.compile(r"^(?:[A-Z0-9_]*METHOD_VERSION|CLASSIFIER)\s*=\s*[\"']", re.MULTILINE)


def _scan_unregistered() -> list[str]:
    registered = {mod for _key, mod, _attr in fp.METHOD_VERSION_PROVIDERS}
    allowed = set(fp.NON_INSTRUMENT_METHOD_MODULES)
    offenders = []
    for path in sorted((Path(config.REPO_ROOT) / "pipeline").glob("*.py")):
        if _METHOD_SYMBOL.search(path.read_text(encoding="utf-8")):
            if path.stem not in registered and path.stem not in allowed:
                offenders.append(path.stem)
    return offenders


def test_method_versions_import_the_live_owning_authorities():
    versions = fp.method_versions()
    assert versions["document_families"] == document_families.METHOD_VERSION == "document-families-v2"
    assert versions["surface_eligibility"] == eligibility.CLASSIFIER == "surface-eligibility-v3"
    assert versions["phrase_statistics"] == surges.METHOD_VERSION
    assert versions["participation"] == participation.METHOD_VERSION
    assert versions["denominators"] == denominators.METHOD_VERSION
    assert versions["shadow_replay"] == shadow_replay.METHOD_VERSION
    assert versions["status_exports"] == status_exports.METHOD_VERSION
    assert versions["structured_composite"] == distill.STRUCTURED_COMPOSITE_VERSION


def test_schema_versions_import_the_live_owning_authorities():
    schemas = fp.schema_versions()
    assert schemas["claim_contract"] == contracts.SCHEMA_VERSION
    assert schemas["corrections"] == corrections.SCHEMA_VERSION == 3


def test_bumping_a_live_method_version_moves_the_fingerprint_with_no_registry_edit():
    base = fp.build()["sha256"]
    original = document_families.METHOD_VERSION
    try:
        document_families.METHOD_VERSION = original + "-probe"
        moved = fp.build()["sha256"]
    finally:
        document_families.METHOD_VERSION = original
    assert moved != base
    assert fp.build()["sha256"] == base


def test_provider_discovery_covers_every_production_method_module():
    assert _scan_unregistered() == [], "a production method module is absent from the registry"


def test_provider_discovery_fails_when_a_provider_is_dropped():
    original = fp.METHOD_VERSION_PROVIDERS
    try:
        fp.METHOD_VERSION_PROVIDERS = tuple(p for p in original if p[0] != "document_families")
        assert "document_families" in _scan_unregistered()
    finally:
        fp.METHOD_VERSION_PROVIDERS = original
    assert _scan_unregistered() == []


def test_code_identity_hashes_the_measurement_tree_not_data_or_site():
    root = Path(config.REPO_ROOT)
    rels = [p.relative_to(root).as_posix() for p in fp.measurement_tree_files()]
    assert rels, "measurement tree is empty"
    assert all(not r.startswith("data/") and not r.startswith("site/") for r in rels)
    assert "pipeline/config.py" in rels
    assert any(r.startswith("pipeline/prompts/") and r.endswith(".txt") for r in rels)
    assert "taxonomy_v1.json" in rels


def test_code_tree_hash_is_deterministic():
    assert fp.code_tree_hash() == fp.code_tree_hash()
    assert len(fp.code_tree_hash()) == 64


def test_day_post_and_api_artifacts_in_one_cycle_carry_one_identical_fingerprint():
    fingerprint = fp.build()
    day_record = fp.stamp({"day": "2026-07-25"}, fingerprint)
    # The post manifest and the API export inherit the day record's stamp.
    post_fingerprint = fp.inherit(day_record)
    envelope = status_exports.envelope(day_record, "2026-07-25T00:00:00Z", fingerprint=post_fingerprint)
    assert day_record["instrument_fingerprint"] == fingerprint
    assert post_fingerprint == fingerprint
    assert envelope["instrument_fingerprint"] == fingerprint
    assert status_exports.verify_envelope(envelope)


def test_experimental_export_instrument_resource_inherits_the_cycle_fingerprint():
    fingerprint = fp.build()
    day = ("2026-07-25", {"day": "2026-07-25", "instrument_fingerprint": fingerprint,
                          "daily_lines": {}, "top_synchronized": []})
    status = {"generated_at": "2026-07-25T00:00:00Z"}
    out = status_exports.experimental_exports(status, [day], {"by_peak": []}, [], fingerprint)
    import json
    instrument = json.loads(out["api/v1/resources/instrument.json"])
    assert instrument["payload"]["instrument_fingerprint"] == fingerprint
    assert instrument["instrument_fingerprint"] == fingerprint


def test_committed_2026_07_25_records_show_the_drift_that_inheritance_removes():
    # The real artifacts the third review cited: the committed post manifest carried a
    # different fingerprint than the day record it posted (verification result 2).
    day_record = util.read_json(config.DERIVED / "days" / "2026-07-25.json", {})
    post_manifest = util.read_json(config.DERIVED / "manifest" / "post-2026-07-25.json", {})
    assert day_record.get("day") == "2026-07-25"
    assert day_record["instrument_fingerprint"] != post_manifest["instrument_fingerprint"]
    # The inheritance path now makes a post manifest carry the day record's exact stamp.
    assert fp.inherit(day_record) == day_record["instrument_fingerprint"]


def test_wrong_method_attestation_correction_is_published():
    rows = corrections.load()
    match = [r for r in rows if r.get("category") == "wrong-method-attestation"]
    assert match, "the Y1 correction is absent from the public ledger"
    entry = match[0]
    assert entry["severity"] == "major"
    assert entry["status"] in corrections.STATUS_CLASSES
    assert entry["schema_version"] == corrections.SCHEMA_VERSION
    assert "2026-07-25" in entry["affected_days"]
    assert all(field in entry for field in corrections.LIFECYCLE_FIELDS)
