"""Mutation harness for every central registry-versus-authority invariant (R-36.1).

Each invariant reads a registry-derived value and its live owning authority. The harness
bumps the owner and asserts the registry follows, which proves the registry is a live read
of its owner and not a stale copy. If a later change reintroduced a hand-copied literal, the
owner bump would not be reflected and the harness would fail, reporting the invariant as no
longer load-bearing.
"""
from __future__ import annotations

from pipeline import instrument_fingerprint as fp
from pipeline import goldset_rater, privacy, privacy_canary, status_exports, util


def _bump(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    return f"{value}-probe"


def _build_invariants() -> list[dict]:
    invariants: list[dict] = []
    for key, module, attr in fp.METHOD_VERSION_PROVIDERS:
        invariants.append({
            "name": f"method_version:{key}",
            "read": (lambda k=key: fp.method_versions()[k]),
            "owner_module": fp._owning_module(module),
            "owner_attr": attr,
        })
    for key, module, attr in fp.SCHEMA_VERSION_PROVIDERS:
        invariants.append({
            "name": f"schema_version:{key}",
            "read": (lambda k=key: fp.schema_versions()[k]),
            "owner_module": fp._owning_module(module),
            "owner_attr": attr,
        })
    # The offline gold-set rating instrument. Its registration is what a published model
    # answer sheet is checked against, so a hand-copied hash there would be the same defect
    # as a stale method version here. ``expect`` covers the derived values: bump the owning
    # text and the registered content address must follow it, not merely change.
    invariants += [
        {"name": "goldset_rater:prompt_version",
         "read": lambda: goldset_rater.registration()["prompt_version"],
         "owner_module": goldset_rater, "owner_attr": "PROMPT_VERSION"},
        {"name": "goldset_rater:model",
         "read": lambda: goldset_rater.registration()["model"],
         "owner_module": goldset_rater, "owner_attr": "MODEL"},
        {"name": "goldset_rater:wrapper_sha256",
         "read": lambda: goldset_rater.registration()["wrapper_sha256"],
         "owner_module": goldset_rater, "owner_attr": "_WRAPPER_TEXT",
         "expect": util.sha256_hex},
        {"name": "goldset_rater:guide_sha256",
         "read": lambda: goldset_rater.registration()["guide_sha256"],
         "owner_module": goldset_rater, "owner_attr": "_GUIDE_TEXT",
         "expect": util.sha256_hex},
        {"name": "goldset_rater:rating_prompt_sha256",
         "read": lambda: goldset_rater.registration()["rating_prompt_sha256"],
         "owner_module": goldset_rater, "owner_attr": "_GUIDE_TEXT",
         "expect": lambda guide: util.sha256_hex(
             f"{goldset_rater.PROMPT_ID}\n{goldset_rater.PROMPT_VERSION}\n"
             f"{goldset_rater.wrapper_text()}\n{guide}")},
    ]
    invariants += [
        {"name": "api_version",
         "read": lambda: status_exports.envelope({"a": 1}, None, fingerprint={})["api_version"],
         "owner_module": status_exports, "owner_attr": "API_VERSION"},
        {"name": "canary_version",
         "read": lambda: privacy_canary.run()["canary_version"],
         "owner_module": privacy_canary, "owner_attr": "CANARY_VERSION"},
        {"name": "entity_hierarchy_version",
         "read": lambda: privacy_canary.run()["entity_hierarchy_version"],
         "owner_module": privacy, "owner_attr": "ENTITY_HIERARCHY_VERSION"},
    ]
    return invariants


REGISTRY_INVARIANTS = _build_invariants()


def run_registry_mutations() -> list[dict]:
    """Bump each owner in turn and prove its registry tracks it, reporting each load-bearing."""
    report = []
    for invariant in REGISTRY_INVARIANTS:
        module, attr = invariant["owner_module"], invariant["owner_attr"]
        expect = invariant.get("expect") or (lambda value: value)
        original = getattr(module, attr)
        baseline = invariant["read"]()
        if baseline != expect(original):
            raise AssertionError(
                f"{invariant['name']} does not match its owner at baseline: {baseline!r} != {original!r}")
        bumped = _bump(original)
        try:
            setattr(module, attr, bumped)
            tracked = invariant["read"]()
            if tracked != expect(bumped):
                raise AssertionError(
                    f"{invariant['name']} did not track its owner; the registry is a stale copy: "
                    f"{tracked!r} != {bumped!r}")
            report.append({"invariant": invariant["name"], "load_bearing": True})
        finally:
            setattr(module, attr, original)
    return report
