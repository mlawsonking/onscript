"""X14 acceptance tests for occurrence context and deterministic stance guards."""
from __future__ import annotations

from pipeline import contracts, eligibility


PHRASE = "stock trading ban"


def _statement(index: int, text: str) -> dict:
    return {
        "id": f"s{index}", "text": text, "published_at": "2026-07-27",
        "member": {"bioguide": f"B{index}", "party": "D"},
        "document_family": {
            "family_id": f"family-{index}", "family_revision": f"revision-{index}",
        },
    }


def _claim(statements: list[dict]) -> dict:
    source = {
        "id": "claim-stock-trading-ban", "label": PHRASE,
        "statements": [row["id"] for row in statements],
        "member_count": len(statements), "topics": ["ethics"],
    }
    return contracts.canonical_claim(source, {row["id"]: row for row in statements})


def test_negated_fixture_never_merges_with_affirmative_as_a_message_claim():
    statements = [
        _statement(1, "This is not a stock trading ban. It is a disclosure rule."),
        _statement(2, "Congress needs a stock trading ban now."),
        _statement(3, "We support a stock trading ban for public trust."),
    ]
    claim = _claim(statements)
    assert {row["stance"] for row in claim["occurrences"]} == {"negated", "affirmative"}
    classified = eligibility.classify_claim(claim, day="2026-07-27")
    assert classified["surface_class"] == "unknown"
    assert classified["classifier"]["rule"] == "mixed-stance"
    selected, _names = eligibility.select_claims([claim], day="2026-07-27")
    assert selected == []


def test_affirmative_counterpart_remains_eligible_when_three_families_support_it():
    claim = _claim([
        _statement(1, "Congress needs a stock trading ban now."),
        _statement(2, "We support a stock trading ban for public trust."),
        _statement(3, "Pass the stock trading ban this week."),
    ])
    classified = eligibility.classify_claim(claim, day="2026-07-27")
    assert classified["surface_class"] == "message"
    assert classified["surface_eligible"] is True


def test_occurrence_carries_sentence_clause_offsets_and_adjacent_tokens():
    statement = _statement(1, "Opening clause, this is not a stock trading ban; closing clause.")
    occurrence = contracts.phrase_occurrences(statement, PHRASE, "claim-1")[0]
    for key in (
        "sentence_start_char", "sentence_end_char", "sentence_offset_start", "sentence_offset_end",
        "clause_start_char", "clause_end_char", "clause_offset_start", "clause_offset_end",
        "adjacent_tokens_before", "adjacent_tokens_after", "is_quoted",
        "quoted_speaker_detected", "stance", "context_version",
    ):
        assert key in occurrence
    text = statement["text"]
    assert text[occurrence["start_char"]:occurrence["end_char"]] == PHRASE
    assert occurrence["adjacent_tokens_before"][-2:] == ["not", "a"]
    assert occurrence["stance"] == "negated"


def test_quote_attribution_only_is_not_the_offices_message():
    statements = [
        _statement(index, 'A witness said, "we need a stock trading ban now."')
        for index in range(1, 4)
    ]
    claim = _claim(statements)
    assert all(row["is_quoted"] and row["quoted_speaker_detected"]
               for row in claim["occurrences"])
    classified = eligibility.classify_claim(claim, day="2026-07-27")
    assert classified["surface_class"] == "unknown"
    assert classified["classifier"]["rule"] == "quoted-attribution-only"
