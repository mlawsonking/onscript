"""W2 canonical occurrences, typed claims, and blocking invariants."""
from __future__ import annotations

from copy import deepcopy
import json

from pipeline import contracts, distill, run_assemble, site, verify


PHRASE = "protect voting rights now"


def _statement(index: int) -> dict:
    sid = f"statement-{index}"
    return {
        "id": sid,
        "text": f"We {PHRASE}. Office {index} agrees.",
        "published_at": "2026-07-24",
        "url": f"https://example.test/{sid}",
        "member": {
            "bioguide": f"M{index:06d}",
            "party": "D",
            "state": "TS",
        },
    }


def _claim() -> tuple[dict, dict[str, dict], dict[str, dict]]:
    statements = [_statement(index) for index in range(1, 4)]
    statement_map = {row["id"]: row for row in statements}
    roster = {
        row["member"]["bioguide"]: {
            "name": f"Member {index}",
            **row["member"],
        }
        for index, row in enumerate(statements, 1)
    }
    legacy = {
        "id": "claim-test-1",
        "label": PHRASE,
        "member_count": 3,
        "statements": list(statement_map),
        "fragments": [
            {"statement": row["id"], "text": PHRASE}
            for row in statements
        ],
        "topics": ["voting"],
    }
    claim = contracts.canonical_claim(legacy, statement_map)
    claim["citations"] = run_assemble._citations(claim, statement_map, roster)
    claim["citation_occurrence_ids"] = [
        row["occurrence_id"] for row in claim["citations"]
    ]
    return claim, statement_map, roster


def test_occurrences_have_exact_character_offsets():
    claim, statement_map, _roster = _claim()
    assert len(claim["occurrences"]) == 3
    for occurrence in claim["occurrences"]:
        source = statement_map[occurrence["statement_id"]]["text"]
        assert source[occurrence["start_char"]:occurrence["end_char"]] == PHRASE


def test_each_of_six_claim_invariants_fails_closed_when_broken():
    claim, statement_map, _roster = _claim()
    ok, reasons = verify.verify_talking_point(
        claim, statement_map, require_contract=True, require_citations=True
    )
    assert ok, reasons

    mutations = {
        "identity": lambda row: row.update(claim_id="wrong-claim"),
        "support_phrase": lambda row: row["support_phrase"].update(normalized="wrong phrase"),
        "occurrence_offsets": lambda row: row["occurrences"][0].update(start_char=0),
        "support_set": lambda row: row["statements"].pop(),
        "unit_counts": lambda row: row["counts"].update(offices=99),
        "render_binding": lambda row: row.update(display_quote="different words"),
    }
    assert len(mutations) == 6
    for invariant, mutate in mutations.items():
        broken = deepcopy(claim)
        mutate(broken)
        passed, broken_reasons = verify.verify_talking_point(
            broken, statement_map, require_contract=True, require_citations=True
        )
        assert not passed, invariant
        assert f"claim-invariant:{invariant}" in broken_reasons


def test_stats_and_sentences_use_typed_claim_ids_and_only_counted_quote():
    claim, statement_map, _roster = _claim()
    stats = distill.build_stats("D", "2026-07-24", 3, [claim], None)
    claim_id = claim["claim_id"]
    assert stats["schema_version"] == 2
    assert stats["claim_ids"] == [claim_id]
    assert stats["talking_points"][0]["quote"] == PHRASE
    rendered = distill._compose_dry(stats)
    # One number per claim sentence, and it is the support count the digit whitelist admits.
    # The three labeled unit counts stay on the day page (receipts_strip, tested below). §S65.
    assert f'3 of us carried "{PHRASE}"' in rendered
    rendered_ok, rendered_reasons = verify.verify_daily_line(
        {"composite": rendered}, json.dumps(stats, ensure_ascii=False), stats=stats
    )
    assert rendered_ok, rendered_reasons
    composite = f'3 of us carried "{PHRASE}."'
    # A model-added character inside the quotation is not the counted phrase.
    assert contracts.sentence_claims(composite, stats)[0]["claim_ids"] == []

    composite = f'3 of us carried "{PHRASE}".'
    mapping = contracts.sentence_claims(composite, stats)
    assert mapping == [{"sentence_idx": 0, "claim_ids": [claim_id]}]
    payload = {"composite": composite, "quiet": False}
    passed, reasons = verify.verify_daily_line(
        payload, json.dumps(stats, ensure_ascii=False), [], stats=stats
    )
    assert passed, reasons


def test_screened_claim_and_receipt_render_three_labeled_units():
    claim, statement_map, roster = _claim()
    legacy = {
        key: value for key, value in claim.items()
        if key not in {
            "schema_version", "object_type", "claim_id", "support_phrase", "display_quote",
            "occurrences", "counts", "office_ids", "publication_ids", "family_ids",
            "support_unit_ids", "citation_occurrence_ids", "citations",
        }
    }
    published, dropped, rejected = run_assemble._screen_talking_points(
        [legacy], statement_map, roster
    )
    assert dropped == 0
    assert rejected == []
    assert published[0]["counts"] == {
        "offices": 3,
        "publications": 3,
        "families": 3,
        "support_units": 3,
    }
    html = site.receipts_strip("D", published)
    assert "3 offices" in html
    assert "3 publications" in html
    assert "3 families" in html
