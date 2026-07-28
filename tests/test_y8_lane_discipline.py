"""Y8 acceptance: lane discipline (R-36.8).

A name, a procedure, or a biography never renders under a heading that says message or
synchronized without the lexical-table disclaimer. The repeated-phrase tables name their
unfiltered nature and carry the disclaimer, on the homepage, the party columns, and day pages.
"""
from __future__ import annotations

from pipeline import config, eligibility, public_strings, site, util


def _day(day):
    return util.read_json(config.DERIVED / "days" / f"{day}.json", {})


def test_the_classifier_tags_the_fixture_rows_as_non_message():
    # The real committed rows the acceptance leans on: a biography and a nomenclature title.
    assert eligibility.classify_phrase("born in the united states", day="2026-06-30")["surface_class"] == "biographical"
    assert eligibility.classify_phrase("water resources development act", day="2026-07-14")["surface_class"] == "nomenclature"


def test_the_day_table_heading_is_disclaimed_in_both_render_paths():
    day_data = _day("2026-06-30")
    saved = config.FEATURES["party_columns"]
    try:
        for flag in (True, False):  # live party columns and the dark sync_table fallback
            config.FEATURES["party_columns"] = flag
            body = site.day_view_body("2026-06-30", day_data, set(), 1)
            assert "Top synchronized phrases" not in body
            assert "Repeated phrase observations" in body
            assert public_strings.LEXICAL_TABLE_DISCLAIMER in body
    finally:
        config.FEATURES["party_columns"] = saved


def test_a_biographical_and_procedural_row_still_render_under_the_disclaimed_heading():
    # Recall is preserved: the flagship 2026-06-30 convergence is not silently dropped; it renders
    # under the honest heading rather than under a message or synchronized label.
    body = site.day_view_body("2026-06-30", _day("2026-06-30"), set(), 1)
    assert "born in the united states" in body        # biographical
    assert "the supreme court" in body                # procedural
    assert "most synchronized</h3>" not in body       # the old party-column sub-heading is gone


def test_a_nomenclature_row_renders_disclaimed_not_synchronized():
    body = site.day_view_body("2026-07-14", _day("2026-07-14"), set(), 1)
    assert "Repeated phrase observations" in body
    assert public_strings.LEXICAL_TABLE_DISCLAIMER in body
    assert "water resources development act" in body


def test_the_phrases_index_disclaims_the_repeated_phrase_table():
    top = {"by_velocity": [], "by_peak": [{
        "ngram": "water resources development act", "party": "D", "day_peak": 5,
        "slug": "s", "velocity": 1.0, "first_seen": {"date": "2026-07-14"}}]}
    body = site.phrases_index_body(top)
    assert "Most synchronized" not in body
    assert "Repeated phrase observations" in body
    assert public_strings.LEXICAL_TABLE_DISCLAIMER in body
    assert "water resources development act" in body
