"""Complete, deterministic identity for the published measurement instrument."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess

from . import config, llm, nomenclature, privacy


FINGERPRINT_VERSION = "instrument-v1"

# These values affect a current measurement or published selection. Constants in
# config that have no production reader are intentionally absent.
LIVE_THRESHOLD_NAMES = (
    "NGRAM_MIN", "NGRAM_MAX", "BOILERPLATE_DF_MIN_DOCS",
    "BOILERPLATE_DF_SHARE_MAX", "LEDGER_MIN_TOTAL_USES", "SYNC_MIN_MEMBERS",
    "DOCUMENT_FAMILY_JACCARD", "DOCUMENT_FAMILY_MIN_TOKENS",
    "DOCUMENT_FAMILY_SHINGLE_K", "DOCUMENT_FAMILY_MINHASHES",
    "DOCUMENT_FAMILY_MINHASH_BANDS", "NOMENCLATURE_RATIO_MIN",
    "SURGE_MIN_ABSOLUTE_CHANGE", "SURGE_MIN_RATIO", "SURGE_MAX_Q_VALUE",
    "NOMENCLATURE_INDEX_CONGRESS_MIN", "NOMENCLATURE_MIN_NAME_CONTENT_TOKENS",
    "COMMITTEE_UNQUALIFIED_MIN_TOKENS", "QUIET_DAY_MAX_STATEMENTS",
    "CONCORDANCE_MIN_STATEMENTS", "CONCORDANCE_RECEIPTS_MAX",
    "CONCORDANCE_PEAK_FLOOR", "UNISON_WINDOW_DAYS", "UNISON_MIN_ACTIVE",
    "UNISON_TOP_N", "UNISON_MEMBERS_SAMPLE", "VOID_TOP_N",
)

# Retained only to reproduce the prior public symmetry component. The new overall
# fingerprint does not hash this compatibility value because it includes a dead knob.
LEGACY_THRESHOLD_NAMES = (
    "SYNC_MIN_MEMBERS", "NGRAM_MIN", "NGRAM_MAX", "BOILERPLATE_DF_SHARE_MAX",
    "NEAR_JOINT_JACCARD", "LEDGER_MIN_TOTAL_USES", "QUIET_DAY_MAX_STATEMENTS",
)

SCHEMA_VERSIONS = {
    "claim_contract": 2,
    "corrections": 2,
    "published_artifact": 1,
}

METHOD_VERSIONS = {
    "document_families": "document-families-v1",
    "gold_set": "gold-set-harness-v1",
    "participation": "participation-measures-v1",
    "phrase_statistics": "phrase-statistics-v2",
    "surface_eligibility": "surface-eligibility-v2",
    "structured_composite": "structured-composite-v1",
    "status_exports": "status-exports-v1",
}


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _hash(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def code_commit() -> str:
    """Return the checked-out commit without making the fingerprint network-dependent."""
    supplied = os.environ.get("GITHUB_SHA", "").strip()
    if supplied:
        return supplied
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=config.REPO_ROOT,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def live_thresholds(overrides: dict | None = None) -> dict:
    values = {name: getattr(config, name) for name in LIVE_THRESHOLD_NAMES}
    values.update(overrides or {})
    return values


def legacy_thresholds_sha(overrides: dict | None = None) -> str:
    values = {name: getattr(config, name) for name in LEGACY_THRESHOLD_NAMES}
    values.update(overrides or {})
    if config.feature_on("nomenclature_tags"):
        values["NOMENCLATURE_RATIO_MIN"] = config.NOMENCLATURE_RATIO_MIN
        version = nomenclature.index_version()
        if version:
            values["nomenclature_index_version"] = version
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode("utf-8")).hexdigest()


def prompt_components() -> dict:
    return {prompt: llm.load_prompt(prompt)["sha"] for prompt in ("P1", "P2", "P3")}


def build(*, threshold_overrides: dict | None = None,
          component_overrides: dict | None = None) -> dict:
    """Build the fingerprint and its inspectable component hashes.

    Overrides exist for deterministic mutation tests. Production callers pass none.
    """
    raw_components = {
        "code_commit": code_commit(),
        "schema_versions": SCHEMA_VERSIONS,
        "method_versions": METHOD_VERSIONS,
        "live_thresholds": live_thresholds(threshold_overrides),
        "prompts": prompt_components(),
        "privacy_forms": privacy.forms_fingerprint(),
        "nomenclature_index": nomenclature.index_version() or "unavailable",
    }
    raw_components.update(component_overrides or {})
    component_hashes = {name: _hash(value) for name, value in raw_components.items()}
    authoritative = {
        "fingerprint_version": FINGERPRINT_VERSION,
        "component_hashes": component_hashes,
    }
    return {
        **authoritative,
        "sha256": _hash(authoritative),
        "thresholds_sha": legacy_thresholds_sha(),
    }


def stamp(payload: dict, fingerprint: dict | None = None) -> dict:
    """Return a shallow copy carrying the authoritative instrument identity."""
    return {**payload, "instrument_fingerprint": fingerprint or build()}
