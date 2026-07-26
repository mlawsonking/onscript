"""W4 person-span suppression before n-gram generation."""
from __future__ import annotations

from pipeline import boilerplate, phrases, privacy
from tests.test_privacy import PERSON_A, PERSON_B, gate


def _plain_grams(text: str) -> set[str]:
    out = set()
    for tokens in boilerplate.sentences(text):
        for size in range(3, 9):
            for index in range(len(tokens) - size + 1):
                out.add(" ".join(tokens[index:index + size]))
    return out


def test_both_historical_escape_shapes_require_span_suppression():
    fixtures = [
        f"policy accountability after the killing of {PERSON_A} needs action now",
        f"policy accountability for {PERSON_B} joan needs action now",
    ]
    with gate():
        for text in fixtures:
            baseline = _plain_grams(text)
            assert any(privacy.is_suppressed(gram) for gram in baseline)
            protected = {gram for gram, _size in phrases._doc_ngrams(text)}
            assert not any(privacy.is_suppressed(gram) for gram in protected)


def test_every_ngram_occurrence_overlapping_a_synthetic_private_span_is_suppressed():
    text = "workers demand fair wages Cedar Vale families deserve safe housing now"
    spans = privacy.person_spans(text, roster_map={})
    held = [row for row in spans if row["classification"] == "quarantine"]
    assert len(held) == 1
    private_interval = (held[0]["start_char"], held[0]["end_char"])

    produced = {gram for gram, _size in phrases._doc_ngrams(text, roster_map={})}
    assert "workers demand fair wages" in produced
    assert "families deserve safe housing" in produced

    tokens = list(boilerplate._TOKEN.finditer(text.lower()))
    for size in range(3, 9):
        for index in range(len(tokens) - size + 1):
            occurrence = (tokens[index].start(), tokens[index + size - 1].end())
            if privacy.intervals_overlap(occurrence, private_interval):
                gram = " ".join(token.group(0) for token in tokens[index:index + size])
                assert gram not in produced


def test_roster_name_passes_only_in_official_context_or_as_the_author():
    roster = {"X000001": {"name": "Ada Lovelace"}}
    titled = "Senator Ada Lovelace supports durable public records"
    casual = "Ada Lovelace supports durable public records"
    authored = {"member": {"bioguide": "X000001"}}

    titled_rows = privacy.person_spans(titled, statement={}, roster_map=roster)
    assert any(row["classification"] == "public_official" for row in titled_rows)
    assert "ada lovelace supports" in {
        gram for gram, _size in phrases._doc_ngrams(titled, statement={}, roster_map=roster)
    }

    casual_rows = privacy.person_spans(casual, statement={}, roster_map=roster)
    assert any(row["classification"] == "quarantine" for row in casual_rows)
    assert not any("ada lovelace" in gram for gram, _size in phrases._doc_ngrams(
        casual, statement={}, roster_map=roster
    ))

    authored_rows = privacy.person_spans(casual, statement=authored, roster_map=roster)
    assert any(row["classification"] == "public_official" for row in authored_rows)


def test_public_allowlist_resolves_a_capitalized_sequence():
    text = "The record cites Sebastian Gorka in official public proceedings"
    rows = privacy.person_spans(text, roster_map={})
    assert any(row["classification"] == "allowlisted" for row in rows)
    assert any("sebastian gorka" in gram for gram, _size in phrases._doc_ngrams(
        text, roster_map={}
    ))
