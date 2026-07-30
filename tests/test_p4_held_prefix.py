"""P4: the held-span prefix reformulation inside _doc_ngrams.

WHY THIS PACKAGE EXISTS. P1's instrumentation showed the W4 span privacy cost is in two places,
not one. Over 2026-06 (4,724 lane-1 units) person_spans itself was 45.7s of the 151.6s spent in
_doc_ngrams, but the per-occurrence held-span interval test inside the n-gram loop was another
36.6s. Caching the admitted-form verdict cannot touch that second half, so the loop was
reformulated: one prefix walk per document answers every occurrence in constant time.

The reformulation is an identity, not an approximation, and these tests pin it that way. They
also pin the precondition it rests on, because on a DEGENERATE (zero length) range the two
formulations genuinely disagree and the engine's guarantee is that it never produces one.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import boilerplate, config, phrases, privacy, scan_cache  # noqa: E402
from tests.test_p3_scan_cache_guards import corpus_from, real_committed_prose  # noqa: E402
from tests.test_privacy import PERSON_A, gate  # noqa: E402


def reference_doc_ngrams(text, statement=None, roster_map=None):
    """_doc_ngrams as it stood before the reformulation: one interval test per occurrence per held
    span. Kept here as the thing production must keep agreeing with."""
    grams = set()
    person_rows = privacy.person_spans(text, statement=statement, roster_map=roster_map)
    held = [(row["start_char"], row["end_char"])
            for row in person_rows if row["classification"] in {"private", "quarantine"}]
    for token_rows in phrases._sentence_token_spans(text):
        toks = [row[0] for row in token_rows]
        for n in range(config.NGRAM_MIN, config.NGRAM_MAX + 1):
            for i in range(0, len(toks) - n + 1):
                occurrence = (token_rows[i][1], token_rows[i + n - 1][2])
                if any(privacy.intervals_overlap(occurrence, span) for span in held):
                    continue
                ng = " ".join(toks[i:i + n])
                if not boilerplate.is_boilerplate_ngram(ng) and not boilerplate.is_low_content(ng):
                    grams.add((ng, n))
    return grams


def test_the_held_prefix_answers_exactly_what_the_interval_scan_answered():
    """The identity the reformulation rests on, checked against the predicate it replaced over
    randomized spans: adjacent, nested, overlapping, and out of range at both ends.

    Both ranges are non-degenerate, which is the domain the engine produces and the domain in
    which the formulations agree exactly. The boundary is pinned by the next test rather than
    assumed: on a zero-length range they genuinely differ, because intervals_overlap reports an
    empty range strictly inside a span as overlapping while a count of shared character positions
    reports none."""
    rng = random.Random(610329)
    for case in range(400):
        length = rng.randint(1, 80)
        text = "x" * length
        held = []
        for _ in range(rng.randint(0, 6)):
            a = rng.randint(-3, length + 3)
            b = a + rng.randint(1, 12)              # non-degenerate, like every real span
            held.append((a, b))
        prefix = phrases._held_prefix(text, held)
        for _ in range(40):
            start = rng.randint(0, length - 1)
            end = rng.randint(start + 1, length)    # non-degenerate, like every real occurrence
            expected = any(privacy.intervals_overlap((start, end), span) for span in held)
            got = prefix[end] > prefix[start]
            assert got == expected, (case, length, held, start, end, expected, got)


def test_no_occurrence_or_held_span_the_engine_produces_is_ever_degenerate():
    """The precondition, asserted rather than assumed.

    An occurrence spans NGRAM_MIN or more non-empty tokens, so its end always exceeds its start;
    a held span comes from a regex match, so the same holds. This is the test that has to fail if
    a future tokenizer or span source starts emitting empty ranges, because that is the day the
    reformulation stops being an identity."""
    assert config.NGRAM_MIN >= 1
    with gate():
        texts = real_committed_prose() + [
            f"Accountability for {PERSON_A} remains an open question in this district.",
            "Contact: press@example.gov -- families deserve safe housing now and always.",
        ]
        checked_occurrences = checked_spans = 0
        for text in texts:
            for row in privacy.person_spans(text, roster_map={}):
                assert row["end_char"] > row["start_char"], (text[:60], row)
                checked_spans += 1
            for token_rows in phrases._sentence_token_spans(text):
                for start_char, end_char in ((row[1], row[2]) for row in token_rows):
                    assert end_char > start_char, (text[:60], start_char, end_char)
                for n in range(config.NGRAM_MIN, config.NGRAM_MAX + 1):
                    for i in range(0, len(token_rows) - n + 1):
                        assert token_rows[i + n - 1][2] > token_rows[i][1]
                        checked_occurrences += 1
        assert checked_occurrences > 500, checked_occurrences
        assert checked_spans > 0, checked_spans


def test_a_held_span_inside_a_stripped_region_still_suppresses_its_occurrences():
    """The case that rules out the cheaper token-level shortcut. Boilerplate stripping blanks
    characters before tokenization, so a held span can land where the phrase tokenizer sees no
    token at all. Character positions answer that correctly; marking held TOKENS would not."""
    with gate():
        text = ("Families across the district deserve safe and affordable housing now. "
                f"Contact: press@example.gov about {PERSON_A} today. "
                "Families across the district deserve safe and affordable housing now.")
        rows = privacy.person_spans(text, roster_map={})
        assert any(row["classification"] == "private" for row in rows), (
            "the fixture must carry an admitted form")
        produced = phrases._doc_ngrams(text, None, {})
        assert produced == reference_doc_ngrams(text, None, {})
        assert not any(privacy.is_suppressed(gram) for gram, _n in produced)


def test_the_reformulation_matches_the_reference_over_real_committed_prose():
    """docs/37 rule 2, applied to the reformulation: real published prose, clean and contaminated."""
    with gate():
        scan_cache.deactivate()
        texts = real_committed_prose()
        assert texts
        contaminated = [f"{t} Accountability for {PERSON_A} remains open." for t in texts[:30]]
        for text in texts + contaminated:
            assert phrases._doc_ngrams(text, None, {}) == reference_doc_ngrams(text, None, {}), (
                text[:80])


def test_the_cache_and_the_reformulation_compose_without_moving_the_output():
    """Both mechanisms active at once, against output built with neither. The cache decides
    whether the admitted-form sweep runs; the prefix decides what its result excludes. A defect in
    either shows up here."""
    import tempfile
    texts = real_committed_prose(limit=60)
    statements = corpus_from(texts, contaminate=True)
    with tempfile.TemporaryDirectory() as raw, gate():
        path = Path(raw) / scan_cache.CACHE_BASENAME
        scan_cache.deactivate()
        reference = {s["id"]: reference_doc_ngrams(s["text"], s, None) for s in statements}

        privacy.activate_scan_cache(path=path)
        try:
            for statement in statements:
                phrases._doc_ngrams(statement["text"], statement, None)
            privacy.flush_scan_cache(path=path)
        finally:
            scan_cache.deactivate()

        privacy.activate_scan_cache(path=path)
        try:
            for statement in statements:
                assert phrases._doc_ngrams(statement["text"], statement, None) == \
                    reference[statement["id"]], statement["id"]
            assert scan_cache.stats()["hits"] > 0
        finally:
            scan_cache.deactivate()
