"""Tests for A4 boilerplate suppression + tokenization (§11.1, §1.4.5)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import boilerplate  # noqa: E402


def test_template_ngrams_flagged():
    for bp in ["today announced the", "issued the following statement", "committee on the judiciary",
               "ranking member of the", "in the 5th congressional district", "unanimous consent to"]:
        assert boilerplate.is_boilerplate_ngram(bp), bp


def test_temporal_ngrams_flagged():
    for bp in ["tuesday july 7", "july 9 2026", "on monday morning", "at 3 30 pm"]:
        assert boilerplate.is_boilerplate_ngram(bp), bp


def test_political_ngrams_survive():
    for good in ["border czar's failed record", "protect social security benefits",
                 "birthright citizenship for every child", "lower prescription drug prices"]:
        assert not boilerplate.is_boilerplate_ngram(good), good


def test_low_content_filler_dropped_but_real_phrases_kept():
    for filler in ["at the same time", "this funding will", "we will continue to", "in order to"]:
        assert boilerplate.is_low_content(filler), filler
    for real in ["war in iran", "birthright citizenship and", "border czar failed record",
                 "lower prescription drug prices"]:
        assert not boilerplate.is_low_content(real), real


def test_modal_may_survives_but_month_with_day_is_flagged():
    assert not boilerplate.is_boilerplate_ngram("we may consider this")   # modal "may" survives
    assert boilerplate.is_boilerplate_ngram("on may 5 we")                 # date "may 5" flagged


def test_clean_text_strips_structural_boilerplate():
    raw = ("FOR IMMEDIATE RELEASE\nContact: press@house.gov (202) 555-0100\n"
           "WASHINGTON, D.C. — Today we protect the border. ###\nignored trailer")
    cleaned = boilerplate.clean_text(raw)
    assert "press@house.gov" not in cleaned
    assert "555" not in cleaned
    assert "ignored trailer" not in cleaned  # dropped after ###


def test_sentences_tokenize_and_drop_dateline():
    sents = list(boilerplate.sentences("WASHINGTON — We will protect the border. Costs are too high!"))
    assert sents[0][:4] == ["we", "will", "protect", "the"]  # dateline stripped
    assert ["costs", "are", "too", "high"] == sents[1]
