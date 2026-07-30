"""W5 adversarial inventory, seeded properties, and verifier mutations."""
from __future__ import annotations

import importlib
import random

from pipeline import contracts, verify
from tests.verifier_mutations import run_mutations


ADVERSARIAL_FIXTURES = {
    "transitive_cluster": ("tests.test_claim_binding", "test_bridged_ndaa_and_insider_topics_publish_only_the_support_set"),
    "component_count": ("tests.test_claim_binding", "test_component_count_cannot_return_as_the_public_numerator"),
    "joint_release": ("tests.test_claim_binding", "test_joint_release_counts_once_in_the_support_set"),
    "syndicated_duplicate": ("tests.test_normalize", "test_syndication_flag"),
    "copied_speaker_quote": ("tests.test_session14", "test_kill_a_colleagues_quote_never_publishes_as_this_members_words"),
    "negation_truncation": ("tests.test_voice", "test_quote_dropping_a_leading_negation_is_rejected"),
    "invented_number": ("tests.test_voice", "test_fabricated_aggregate_from_a_quote_number_is_rejected"),
    "combined_quote_pool": ("tests.test_claim_binding", "test_combined_pool_grounding_cannot_bind_the_wrong_count_to_a_quote"),
    "private_person_span": ("tests.test_w4_span_privacy", "test_both_historical_escape_shapes_require_span_suppression"),
    "stale_archive": ("tests.test_w3_publication", "test_stale_repository_file_in_archive_is_ignored_and_the_day_survives"),
    "archive_traversal": ("tests.test_w3_publication", "test_archive_member_outside_allowlist_is_rejected"),
    "published_day_rollback": ("tests.test_final_immutable", "test_published_day_is_byte_identical_after_a_run_a_pass"),
    # A cached "this text contains no admitted form" verdict that outlives the form list it was
    # computed under is a published name. The cache key commits to the instrument so it cannot.
    "stale_clean_verdict": ("tests.test_p2_scan_cache", "test_a_newly_admitted_form_voids_every_prior_clean_verdict"),
}


def test_adversarial_fixture_inventory_is_complete_and_callable():
    assert len(ADVERSARIAL_FIXTURES) == 13
    for fixture_class, (module_name, function_name) in ADVERSARIAL_FIXTURES.items():
        function = getattr(importlib.import_module(module_name), function_name, None)
        assert callable(function), fixture_class


def test_seeded_random_claims_preserve_offsets_counts_and_contracts():
    rng = random.Random(290051)
    vocabulary = ["protect", "workers", "secure", "ballots", "lower", "costs", "restore", "rights"]
    separators = [" ", ", "]
    for case in range(40):
        words = rng.sample(vocabulary, 4)
        phrase = " ".join(words)
        publications = rng.randint(3, 8)
        statements = {}
        statement_ids = []
        fragments = []
        support_units = set()
        for index in range(publications):
            sid = f"seed-{case}-{index}"
            rendered = "".join(
                word + (rng.choice(separators) if position < len(words) - 1 else "")
                for position, word in enumerate(words)
            )
            joint_group = f"joint-{case}" if index >= 3 and rng.random() < 0.4 else None
            office = f"B{case:03d}{index:03d}"
            statement = {
                "id": sid,
                "text": f"Our office will {rendered} for every community.",
                "published_at": "2026-07-24",
                "joint_group": joint_group,
                "member": {"bioguide": office, "party": "D", "state": "TS"},
            }
            statements[sid] = statement
            statement_ids.append(sid)
            fragments.append({"statement": sid, "text": rendered})
            support_units.add(joint_group or office)
        legacy = {
            "id": f"seeded-claim-{case}",
            "label": phrase,
            "member_count": len(support_units),
            "statements": statement_ids,
            "fragments": fragments,
        }
        claim = contracts.canonical_claim(legacy, statements)
        passed, reasons = verify.verify_talking_point(claim, statements, require_contract=True)
        assert passed, (case, reasons)
        for occurrence in claim["occurrences"]:
            source = statements[occurrence["statement_id"]]["text"]
            assert source[occurrence["start_char"]:occurrence["end_char"]] == occurrence["surface_text"]


def test_seeded_transitive_bridges_never_inflate_the_support_count():
    rng = random.Random(290052)
    phrase = "shared policy action"
    for case in range(30):
        statements = {}
        ids = []
        fragments = []
        support = rng.randint(3, 6)
        bridges = rng.randint(1, 8)
        for index in range(support + bridges):
            sid = f"bridge-{case}-{index}"
            carries = index < support
            text = (f"We demand {phrase} this year."
                    if carries else f"We discuss unrelated bridge topic {case} {index} today.")
            statements[sid] = {
                "id": sid,
                "text": text,
                "member": {"bioguide": f"C{case:03d}{index:03d}", "party": "R"},
            }
            ids.append(sid)
            fragments.append({"statement": sid, "text": text})
        claim = {
            "id": f"bridge-claim-{case}",
            "label": phrase,
            "member_count": support,
            "statements": ids,
            "fragments": fragments,
        }
        assert len(verify.key_carrying_units(claim, statements)) == support
        passed, reasons = verify.verify_talking_point(claim, statements)
        assert passed, reasons
        inflated = dict(claim, member_count=support + bridges)
        assert not verify.verify_talking_point(inflated, statements)[0]


def test_mutation_harness_reports_every_verifier_check_load_bearing():
    report = run_mutations()
    assert [row["check"] for row in report] == list(verify.VERIFIER_CHECKS)
    assert all(row["load_bearing"] is True for row in report)
