"""Mutation harness for every named production verifier check."""
from __future__ import annotations

from copy import deepcopy
import json

from pipeline import contracts, distill, verify
from tests.test_w2_claim_contract import PHRASE, _claim


def _legacy_claim(count: int = 3) -> tuple[dict, dict[str, dict]]:
    canonical, statements, _roster = _claim()
    claim = {
        "id": canonical["id"],
        "label": canonical["label"],
        "member_count": count,
        "statements": list(canonical["statements"]),
        "fragments": deepcopy(canonical["fragments"]),
    }
    return claim, statements


def _valid_stats() -> dict:
    claim, _statements, _roster = _claim()
    return distill.build_stats("D", "2026-07-24", 3, [claim], None)


def _daily_ok(composite: str, stats: dict) -> bool:
    return verify.verify_daily_line(
        {"composite": composite}, json.dumps(stats, ensure_ascii=False), stats=stats
    )[0]


def _claim_mutation(name: str) -> bool:
    claim, statements, _roster = _claim()
    if name == "claim_identity":
        claim["claim_id"] = "wrong-claim"
    elif name == "claim_support_phrase":
        claim["support_phrase"]["normalized"] = "wrong phrase"
    elif name == "claim_occurrence_offsets":
        claim["occurrences"][0]["start_char"] = 0
    elif name == "claim_support_set":
        claim["statements"].append("missing-statement")
    elif name == "claim_unit_counts":
        claim["counts"]["offices"] = 99
    elif name == "claim_render_binding":
        claim["display_quote"] = "different words"
    return verify.verify_talking_point(
        claim, statements, require_contract=True, require_citations=True
    )[0]


def probe(name: str) -> bool:
    """Return whether a deliberately invalid artifact passes the named verifier path."""
    if name.startswith("claim_"):
        return _claim_mutation(name)
    if name == "key_quorum":
        claim, statements = _legacy_claim(count=2)
        claim["statements"] = claim["statements"][:2]
        claim["fragments"] = claim["fragments"][:2]
        return verify.verify_talking_point(claim, statements)[0]
    if name == "support_count":
        claim, statements = _legacy_claim(count=99)
        return verify.verify_talking_point(claim, statements)[0]
    if name == "fragment_verbatim":
        claim, statements = _legacy_claim()
        claim["fragments"][0]["text"] = "invented fragment words"
        return verify.verify_talking_point(claim, statements)[0]
    if name == "number_whitelist":
        stats = _valid_stats()
        return _daily_ok(f'999 offices carried "{PHRASE}".', stats)
    if name == "quote_binding":
        stats = {
            "schema_version": 1,
            "statements": 3,
            "talking_points": [{"label": PHRASE, "quote": PHRASE, "members": 3}],
        }
        return _daily_ok('Offices carried "different unsupported words".', stats)
    if name == "quote_grounding":
        return verify.verify_daily_line(
            {"composite": 'Offices carried "different unsupported words".'}, "{}",
            [PHRASE],
        )[0]
    if name == "typed_claim_ids":
        stats = _valid_stats()
        stats["talking_points"][0]["claim_type"] = "untyped"
        return _daily_ok(f'3 offices carried "{PHRASE}".', stats)
    if name == "sentence_claim_mapping":
        stats = _valid_stats()
        second = deepcopy(stats["talking_points"][0])
        second.update({
            "claim_id": "claim-test-2",
            "label": "secure ballot access now",
            "quote": "secure ballot access now",
        })
        stats["talking_points"].append(second)
        stats["claim_ids"].append(second["claim_id"])
        return _daily_ok(
            f'3 offices carried "{PHRASE}" and "secure ballot access now".', stats
        )
    if name == "counted_phrase_quote":
        stats = _valid_stats()
        stats["talking_points"][0]["quote"] = PHRASE + " and forever"
        return _daily_ok(f'3 offices carried "{PHRASE}".', stats)
    raise KeyError(name)


def run_mutations() -> list[dict]:
    """Disable each check in turn and prove its negative fixture then defeats the suite assertion."""
    report = []
    for name in verify.VERIFIER_CHECKS:
        if probe(name):
            raise AssertionError(f"baseline negative fixture passed: {name}")
        with verify.mutation_disabled(name):
            try:
                assert not probe(name), f"negative fixture escaped when {name} was disabled"
            except AssertionError:
                report.append({"check": name, "load_bearing": True})
            else:
                raise AssertionError(f"mutant survived without failing its suite assertion: {name}")
    return report
