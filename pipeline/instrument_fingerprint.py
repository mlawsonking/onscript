"""Complete, deterministic identity for the published measurement instrument.

Code identity is a content hash over the measurement tree (pipeline code,
prompts, taxonomy, schemas), not repository HEAD. Data commits move HEAD without
changing the instrument, so HEAD is not a truthful code identity (docs/37 rule 7).
Method and schema versions are read from their owning modules, never copied as
strings, so the registry cannot silently misdescribe the live instrument
(docs/36 R-36.1, Constitution Article XVII).
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

from . import config, llm, nomenclature, privacy


FINGERPRINT_VERSION = "instrument-v1"

# These values affect a current measurement or published selection. Constants in
# config that have no production reader are intentionally absent.
LIVE_THRESHOLD_NAMES = (
    "NGRAM_MIN", "NGRAM_MAX", "BOILERPLATE_DF_MIN_DOCS",
    "BOILERPLATE_DF_SHARE_MAX", "LEDGER_MIN_TOTAL_USES", "SYNC_MIN_MEMBERS",
    "DOCUMENT_FAMILY_JACCARD", "DOCUMENT_FAMILY_MIN_TOKENS",
    "DOCUMENT_FAMILY_SHINGLE_K", "DOCUMENT_FAMILY_MINHASHES",
    "DOCUMENT_FAMILY_MINHASH_BANDS", "DOCUMENT_FAMILY_WINDOW_HOURS",
    "DOCUMENT_FAMILY_RECALL_TARGET", "NOMENCLATURE_RATIO_MIN",
    "SURGE_MIN_ABSOLUTE_CHANGE", "SURGE_MIN_RATIO", "SURGE_MAX_Q_VALUE",
    "NOMENCLATURE_INDEX_CONGRESS_MIN", "NOMENCLATURE_MIN_NAME_CONTENT_TOKENS",
    "COMMITTEE_UNQUALIFIED_MIN_TOKENS", "QUIET_DAY_MAX_STATEMENTS",
    "CONCORDANCE_MIN_STATEMENTS", "CONCORDANCE_RECEIPTS_MAX",
    "CONCORDANCE_PEAK_FLOOR", "UNISON_WINDOW_DAYS", "UNISON_MIN_ACTIVE",
    "UNISON_TOP_N", "UNISON_MEMBERS_SAMPLE", "VOID_TOP_N",
    "SHADOW_FALLBACK_RATE_CEILING",
)

# Retained only to reproduce the prior public symmetry component. The new overall
# fingerprint does not hash this compatibility value because it includes a dead knob.
LEGACY_THRESHOLD_NAMES = (
    "SYNC_MIN_MEMBERS", "NGRAM_MIN", "NGRAM_MAX", "BOILERPLATE_DF_SHARE_MAX",
    "NEAR_JOINT_JACCARD", "LEDGER_MIN_TOTAL_USES", "QUIET_DAY_MAX_STATEMENTS",
)

# Each method-version entry is (registry key, owning pipeline module, authority
# symbol). The registry reads the live symbol; it never copies the version string.
# A provider-discovery test scans the pipeline for method-version symbols and fails
# when a production module is neither registered here nor allowlisted below.
METHOD_VERSION_PROVIDERS = (
    ("document_families", "document_families", "METHOD_VERSION"),
    ("surface_eligibility", "eligibility", "CLASSIFIER"),
    ("phrase_statistics", "surges", "METHOD_VERSION"),
    ("participation", "participation", "METHOD_VERSION"),
    ("denominators", "denominators", "METHOD_VERSION"),
    ("gold_set", "goldset", "METHOD_VERSION"),
    ("structured_composite", "distill", "STRUCTURED_COMPOSITE_VERSION"),
    ("shadow_replay", "shadow_replay", "METHOD_VERSION"),
    ("status_exports", "status_exports", "METHOD_VERSION"),
)

# Modules that declare a method-version symbol but are not part of the daily
# published instrument. Provider discovery allows these and records the reason.
NON_INSTRUMENT_METHOD_MODULES = {
    "goldset_bundle": "offline gold-set bundle builder, not a daily published surface",
    "goldset_metrics": "offline gold-set evaluation metrics, not a daily published surface",
    "goldset_sample": "offline gold-set sampling, not a daily published surface",
}

# Schema-version entries import from their owning modules. Every entry has an owner.
SCHEMA_VERSION_PROVIDERS = (
    ("claim_contract", "contracts", "SCHEMA_VERSION"),
    ("corrections", "corrections", "SCHEMA_VERSION"),
    ("published_artifact", "status_exports", "ENVELOPE_SCHEMA_VERSION"),
)


def _owning_module(name: str):
    return importlib.import_module(f"{__package__}.{name}")


def method_versions() -> dict:
    """Return the live method versions read from their owning modules."""
    return {key: getattr(_owning_module(mod), attr)
            for key, mod, attr in METHOD_VERSION_PROVIDERS}


def schema_versions() -> dict:
    """Return the live schema versions read from their owning modules."""
    return {key: getattr(_owning_module(mod), attr)
            for key, mod, attr in SCHEMA_VERSION_PROVIDERS}


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _hash(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


# The measurement tree: pipeline code and prompts, plus the taxonomy and schema
# files. Never data output or the rendered site, so a data-only commit does not
# move the code identity (docs/36 Y1, docs/37 rule 7).
MEASUREMENT_TREE_EXTRA = ("taxonomy_v1.json", "evaluation/annotation.schema.json")
_MEASUREMENT_TREE_SUFFIXES = frozenset({".py", ".txt"})


def measurement_tree_files() -> list[Path]:
    """Return the source files whose content defines the instrument identity."""
    root = config.REPO_ROOT
    files: list[Path] = []
    for path in (root / "pipeline").rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix in _MEASUREMENT_TREE_SUFFIXES:
            files.append(path)
    for relative in MEASUREMENT_TREE_EXTRA:
        extra = root / relative
        if extra.is_file():
            files.append(extra)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def code_tree_hash() -> str:
    """Content hash over the measurement tree with normalized line endings.

    Line endings are normalized to LF so a CRLF checkout and an LF checkout of the
    same source produce the same identity.
    """
    root = config.REPO_ROOT
    digest = hashlib.sha256()
    for path in measurement_tree_files():
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def inherit(source: dict | None) -> dict:
    """Return the instrument identity a prior stage stamped, never a fresh build.

    Downstream artifacts of one cycle (post manifest, exports) carry the exact
    fingerprint assembly stamped, so day, post, and API artifacts agree byte for
    byte (docs/37 rule 6).
    """
    fingerprint = (source or {}).get("instrument_fingerprint")
    if not isinstance(fingerprint, dict):
        raise ValueError("no stamped instrument fingerprint to inherit")
    return fingerprint


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
        "code_tree": code_tree_hash(),
        "schema_versions": schema_versions(),
        "method_versions": method_versions(),
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
