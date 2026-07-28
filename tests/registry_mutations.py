"""Mutation harness for every central registry-versus-authority invariant (R-36.1).

Each invariant reads a registry-derived value and its live owning authority. The harness
bumps the owner and asserts the registry follows, which proves the registry is a live read
of its owner and not a stale copy. If a later change reintroduced a hand-copied literal, the
owner bump would not be reflected and the harness would fail, reporting the invariant as no
longer load-bearing.
"""
from __future__ import annotations

from pipeline import instrument_fingerprint as fp
from pipeline import (config, goldset_rater, llm, privacy, privacy_canary, shadow_replay,
                      status_exports, util)


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
    # The shadow-replay instrument. A live replay is refused unless the four prompt texts hash
    # to the frozen registration, so the registration must be a live read of those texts. If it
    # ever became a hand-copied hash, an edited candidate prompt could spend money under the
    # identity of the prompt that was frozen (docs/33 R-33.6, docs/37 rules 6 and 7).
    invariants += [
        {"name": "shadow_replay:method_version",
         "read": lambda: shadow_replay.registration()["method_version"],
         "owner_module": shadow_replay, "owner_attr": "METHOD_VERSION"},
        {"name": "shadow_replay:model",
         "read": lambda: shadow_replay.registration()["model"],
         "owner_module": llm, "owner_attr": "VOICE_MODEL"},
        {"name": "shadow_replay:fallback_rate_ceiling",
         "read": lambda: shadow_replay.registration()["fallback_rate_ceiling"],
         "owner_module": config, "owner_attr": "SHADOW_FALLBACK_RATE_CEILING"},
        {"name": "shadow_replay:min_complete_days",
         "read": lambda: shadow_replay.registration()["minimums"]["complete_days"],
         "owner_module": shadow_replay, "owner_attr": "MIN_COMPLETE_DAYS"},
        {"name": "shadow_replay:min_party_days",
         "read": lambda: shadow_replay.registration()["minimums"]["party_days"],
         "owner_module": shadow_replay, "owner_attr": "MIN_PARTY_DAYS"},
    ]
    for prompt_id, side, attr in (
        ("P2", "live", "_P2_LIVE_TEXT"), ("P2", "candidate", "_P2_CANDIDATE_TEXT"),
        ("P3", "live", "_P3_LIVE_TEXT"), ("P3", "candidate", "_P3_CANDIDATE_TEXT"),
    ):
        invariants.append({
            "name": f"shadow_replay:prompt_sha256:{prompt_id}:{side}",
            "read": (lambda p=prompt_id, s=side:
                     shadow_replay.registration()["prompt_inventory"][p][s]["sha256"]),
            "owner_module": shadow_replay, "owner_attr": attr,
            "expect": util.sha256_hex,
        })
    # The combined address, checked against an INDEPENDENT reimplementation of the composition.
    # The per-prompt invariants above prove each hash reads its live text; this one proves the
    # whole-instrument address still composes those texts in the documented order.
    invariants.append({
        "name": "shadow_replay:replay_prompt_sha256",
        "read": lambda: shadow_replay.registration()["replay_prompt_sha256"],
        "owner_module": shadow_replay, "owner_attr": "_P2_CANDIDATE_TEXT",
        "expect": lambda text: util.sha256_hex("\n".join([
            shadow_replay.METHOD_VERSION,
            f"P2:live:{shadow_replay._P2_LIVE_TEXT}",
            f"P2:candidate:{text}",
            f"P3:live:{shadow_replay._P3_LIVE_TEXT}",
            f"P3:candidate:{shadow_replay._P3_CANDIDATE_TEXT}",
        ])),
    })
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
