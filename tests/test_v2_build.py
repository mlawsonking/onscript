"""Tests for the v2 Build Program dark shelf (docs/11). Every feature: built + verified + registered
`built/verified/UNRELEASED` behind the FEATURES flag. These lock the render logic and the build-dark
gate (nothing renders publicly until Michael flips the flag)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, gdelt, silence, site  # noqa: E402


# --- 1.1 The Archive -----------------------------------------------------------------------------
def test_archive_index_renders_both_parties_and_fingerprints():
    chapters = [
        {"kind": "era", "congress": 119, "party": "D", "label": "119th", "id": "era-119-D",
         "stats": {"statements": 100, "top_phrases": [
             {"phrase": "birthright citizenship", "peak_members": 30, "first_date": "2025-06-30"}]},
         "verifier": {"passed": True}},
        {"kind": "era", "congress": 119, "party": "R", "label": "119th", "id": "era-119-R",
         "stats": {"statements": 80, "top_phrases": [
             {"phrase": "the southern border", "peak_members": 25, "first_date": "2025-02-01"}]},
         "verifier": {"passed": True}},
    ]
    body = site.archive_index_body(chapters)
    assert "Era fingerprints" in body
    assert "birthright citizenship" in body and "the southern border" in body   # both parties' fingerprints
    assert "pill D" in body and "pill R" in body


def test_chapter_page_renders_essay_phrase_table_and_verifier_note():
    ch = {"kind": "era", "label": "110th", "party": "R", "id": "era-110-R", "generator": "g",
          "prompt_version": "era.v1", "text": "We spoke of energy.\nAnd of war.",
          "verifier": {"passed": True}, "stats": {"statements": 50, "top_phrases": [
              {"phrase": "energy independence", "peak_members": 14, "peak_day": "2007-08-03",
               "first_date": "2007-08-03", "first_sayer": "Sen. X"}]}}
    body = site.chapter_page_body(ch)
    assert "We spoke of energy." in body and "And of war." in body        # essay paragraphs
    assert "energy independence" in body and "Sen. X" in body             # phrase table + receipts
    assert "verifier: passed" in body                                     # the gate is disclosed


def test_archive_loader_is_the_verifier_gate():
    """The release gate is 'zero uncited fragments' -> _load_chapters returns ONLY verifier.passed."""
    chapters = site._load_chapters()
    assert chapters and all((c.get("verifier") or {}).get("passed") for c in chapters)


def test_archive_ships_dark():
    assert config.feature_on("archive") is False    # build-dark: no public render until the flag flips


# --- 1.2 Silence Detector + "Shouting Into the Void" ---------------------------------------------
def _tax():
    return {"topics": [{"id": "immigration", "label": "Immigration", "seeds": ["border", "migrant"]},
                       {"id": "china", "label": "China", "seeds": ["china"]},
                       {"id": "other", "label": "Other", "seeds": []}]}


def _stmts(n, party, text):
    return [{"member": {"party": party}, "title": "", "text": text} for _ in range(n)]


def test_corpus_topics_matches_deterministically_by_committed_seeds():
    stmts = _stmts(3, "D", "the border crisis") + _stmts(2, "R", "trade with china")
    c = silence.corpus_topics(stmts, _tax())
    assert c["immigration"] == {"D": 3, "R": 0} and c["china"] == {"D": 0, "R": 2}


def test_silence_requires_news_AND_both_parties_quiet():
    """Silence = the news is loud and BOTH parties are quiet. One party talking = not a silence."""
    corpus = {"immigration": {"D": 0, "R": 0}, "china": {"D": 40, "R": 0}}
    corpus.update({k: corpus.get(k, {"D": 0, "R": 0}) for k in ("immigration", "china")})
    # pad the day so it clears the corpus-thinness gate
    corpus["china"] = {"D": 40, "R": 40}
    board = silence.silence_board({"immigration": 0.9, "china": 0.9}, corpus, _tax())
    assert board["scored"] is True
    assert [r["topic"] for r in board["silent"]] == ["immigration"]   # china is loudly spoken -> not silent


def test_a_failed_news_pull_is_excluded_not_called_silence():
    """THE guard: a gap is not a silence. A failed GDELT pull (None) must never produce a claim."""
    corpus = {"immigration": {"D": 0, "R": 0}, "china": {"D": 40, "R": 40}}
    board = silence.silence_board({"immigration": None, "china": 0.9}, corpus, _tax())
    assert board["silent"] == []                                     # no claim from a failed pull
    assert board["excluded"] and board["excluded"][0]["topic"] == "immigration"


def test_a_thin_or_one_party_day_is_not_scored():
    """A corpus hole must never masquerade as avoidance — thin days score nothing, both directions."""
    corpus = {"immigration": {"D": 0, "R": 0}, "china": {"D": 3, "R": 0}}
    board = silence.silence_board({"immigration": 0.9, "china": 0.9}, corpus, _tax())
    assert board["scored"] is False and board["silent"] == [] and board["void"] == []
    assert "thin" in board["gates"]["note"]


def test_void_is_the_mirror_twin_and_ships_with_silence():
    """Both directions ship together: the same call returns silent[] and void[]."""
    corpus = {"immigration": {"D": 0, "R": 0}, "china": {"D": 40, "R": 40}}
    board = silence.silence_board({"immigration": 0.9, "china": 0.0}, corpus, _tax())
    assert [r["topic"] for r in board["silent"]] == ["immigration"]
    assert [r["topic"] for r in board["void"]] == ["china"]          # loud for us, absent from the news
    assert "silent" in board and "void" in board


def test_theme_map_is_committed_and_shares_the_taxonomy_seeds():
    """The published topic definition is ONE list: the same seeds drive the news query and our match —
    that's what makes a silence claim reproducible from published data."""
    m = gdelt.load_theme_map()
    tax = {t["id"]: t for t in silence.load_taxonomy()["topics"]}
    assert m["topics"] and "other" not in m["topics"]                # a catch-all has no news baseline
    for tid, spec in m["topics"].items():
        assert spec["seeds"] == tax[tid]["seeds"]                    # one definition, both sides
        assert "sourcecountry:unitedstates" in spec["query"]


def test_silence_board_ships_dark():
    assert config.feature_on("silence_board") is False


def test_silence_render_ships_both_directions_together():
    """The release gate: silence and its mirror twin render on the SAME page, or not at all."""
    board = {"day": "2026-07-16", "scored": True,
             "silent": [{"topic": "immigration", "label": "Immigration", "news_volume": 0.9, "D": 0, "R": 0}],
             "void": [{"topic": "china", "label": "China", "news_volume": 0.0, "D": 40, "R": 40}],
             "excluded": [], "gates": {"news_floor": 0.05, "quiet_max": 2, "void_min": 5,
                                       "void_news_max": 0.01}}
    body = site.silence_board_body(board)
    assert "Nobody will say it" in body and "Shouting into the void" in body   # both directions, one page
    assert "Immigration" in body and "China" in body
    assert "A gap is not a silence" in body                                    # the guard is disclosed


def test_silence_render_refuses_to_score_without_a_baseline():
    """An unscored board must say so plainly — never render an empty silence list as 'nobody spoke'."""
    body = site.silence_board_body({"day": "2026-07-16", "scored": False,
                                    "gates": {"note": "no news baseline for this day"}})
    assert "Not scored for this day" in body and "no news baseline" in body
    assert "Nobody will say it" not in body                                   # no claim is rendered


def test_build_day_board_without_baseline_is_unscored_not_fabricated():
    board = silence.build_day_board("1999-01-01", _stmts(50, "D", "the border") + _stmts(50, "R", "china"))
    assert board["scored"] is False and board["silent"] == [] and board["void"] == []
