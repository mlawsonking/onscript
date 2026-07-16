"""Tests for the v2 Build Program dark shelf (docs/11). Every feature: built + verified + registered
`built/verified/UNRELEASED` behind the FEATURES flag. These lock the render logic and the build-dark
gate (nothing renders publicly until Michael flips the flag)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, site  # noqa: E402


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
