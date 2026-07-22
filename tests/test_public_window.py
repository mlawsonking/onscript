"""D3/D4 regression tests: public phrase statistics use one explicit Stage-1 window."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from pipeline import config, site


PRE_EPOCH = "2013-04-17"
FIRST_PUBLIC = "2025-01-05"
PUBLIC_PEAK_DAY = "2026-02-09"


def _mixed_phrase(slug="mixed"):
    return {
        "ngram": "equal justice under law",
        "slug": slug,
        "first_seen": {"date": PRE_EPOCH, "bioguide": "S001168", "tie": ["H000001"]},
        "peak_units": 99,
        "df_weight": 0.84,
        "series": [
            {"day": PRE_EPOCH, "D": 99, "R": 0, "I": 0},
            {"day": FIRST_PUBLIC, "D": 3, "R": 0, "I": 0},
            {"day": PUBLIC_PEAK_DAY, "D": 1, "R": 7, "I": 0},
        ],
    }


def _index_from(payloads: list[dict]) -> list[dict]:
    with tempfile.TemporaryDirectory() as td:
        pdir = Path(td) / "phrases"
        pdir.mkdir()
        for i, payload in enumerate(payloads):
            (pdir / f"p{i}.json").write_text(json.dumps(payload), encoding="utf-8")
        old = site.DERIVED
        site.DERIVED = Path(td)
        try:
            return site.phrase_search_index()
        finally:
            site.DERIVED = old


def test_kill_pre_epoch_peak_and_sayer_never_render_and_input_stays_intact():
    phrase = _mixed_phrase()
    original = copy.deepcopy(phrase)
    html = site.phrase_page_body(phrase)

    assert phrase == original
    assert PRE_EPOCH not in html
    assert "S001168" not in html and "H000001" not in html
    assert "99 members in one day" not in html
    assert "7 members in one day" in html
    assert FIRST_PUBLIC in html and "first active day in the public window" in html


def test_search_index_and_page_use_the_same_public_peak_and_first_day():
    phrase = _mixed_phrase("same-stats")
    rows = _index_from([phrase])
    assert rows == [{"q": phrase["ngram"], "s": "same-stats", "p": 7, "f": FIRST_PUBLIC}]
    html = site.phrase_page_body(phrase)
    assert f">{rows[0]['p']} members in one day<" in html
    assert rows[0]["f"] in html


def test_zero_in_window_phrase_keeps_page_but_is_not_searchable():
    phrase = _mixed_phrase("historical-only")
    phrase["series"] = phrase["series"][:1]
    rows = _index_from([phrase])
    html = site.phrase_page_body(phrase)

    assert rows == []
    assert "No observations in the public window" in html
    assert phrase["ngram"] in html
    assert PRE_EPOCH not in html


def test_member_name_never_falls_back_to_a_raw_bioguide_id():
    missing = "S001168"
    old = site.ROSTER
    site.ROSTER = {}
    try:
        rendered = site.member_name(missing)
    finally:
        site.ROSTER = old
    assert missing not in rendered
    assert "unavailable" in rendered


def test_dark_surface_renderers_never_style_a_bare_bioguide_as_a_name():
    missing = "S001168"
    row = {"bioguide": missing, "name": missing, "party": "D", "state": "CA",
           "chamber": "house", "statements": 12, "on_script": 5, "index": 5 / 12}
    old = site.ROSTER
    site.ROSTER = {}
    try:
        concordance = site._member_label(row)
        unison = site._unison_offices({"members": [row], "offices_using": 1})
    finally:
        site.ROSTER = old
    assert missing not in concordance
    assert missing not in unison
    assert "unavailable" in concordance and "unavailable" in unison


def test_methodology_coverage_and_phrase_disclosure_name_the_same_window():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "coverage.json").write_text(json.dumps({
            "2014": {"D": 4, "R": 5, "I": 0},
            "2025": {"D": 40, "R": 50, "I": 0},
        }), encoding="utf-8")
        old = site.DERIVED
        site.DERIVED = root
        try:
            methodology = site.methodology_body()
        finally:
            site.DERIVED = old
    phrase = site.phrase_page_body(_mixed_phrase())

    assert config.STAGE1_EPOCH in methodology and config.STAGE1_EPOCH in phrase
    assert "<td>2014</td>" not in methodology
    assert "<td>2025</td>" in methodology
