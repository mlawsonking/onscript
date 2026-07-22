"""1.7b Phrase search — the release gate and the two injection defenses. All $0, no network.

Every phrase in the index is UNTRUSTED text lifted from a press release, and it is embedded directly
into the page, so the escaping here is load-bearing rather than theoretical. Both defenses were also
exercised against a live DOM (a hostile phrase rendered no element and fired no handler); these tests
are the regression floor for that result.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, site  # noqa: E402

_EVIL = '</script><img src=x onerror="window.__pwned=1">'
_ROWS = [{"q": _EVIL, "s": "e1", "p": 9, "f": "2026-01-01"},
         {"q": "rule of law", "s": "2806979f9276012b", "p": 7, "f": "2026-01-03"}]


def test_untrusted_phrase_cannot_close_the_script_element():
    """A phrase containing "</script>" would otherwise end the JSON block early and let the rest of
    the phrase run as markup. "<" is escaped, so the element can only be closed by us."""
    html = site.phrase_search_body(_ROWS)
    assert "</script><img" not in html          # the raw breakout never appears...
    assert "\\u003c/script" in html             # ...it is escaped instead
    # and the payload is still valid JSON that a browser will parse back to the original text
    start = html.index('type="application/json">') + len('type="application/json">')
    payload = html[start:html.index("</script>", start)]
    assert json.loads(payload)[0]["q"] == _EVIL


def test_results_are_built_as_text_never_markup():
    """innerHTML on a phrase would execute it; textContent renders it as the text it is."""
    html = site.phrase_search_body(_ROWS)
    assert "innerHTML" not in html
    assert "textContent" in html and "createElement" in html


def test_index_only_contains_phrases_that_have_pages():
    """A result must always open a real page: the index is built from the phrase-page JSONs, so it can
    never advertise a phrase whose page 404s."""
    rows = site.phrase_search_index()
    slugs = site.phrase_page_slugs()
    assert rows, "expected real phrase pages in data/derived/phrases"
    for r in rows:
        assert r["s"] in slugs, r
    # ranked by coordination magnitude, strongest first
    peaks = [r["p"] for r in rows]
    assert peaks == sorted(peaks, reverse=True)


def test_search_page_is_dark_until_its_flag_flips():
    """Build dark / release by gate. The page must be ABSENT from the output while dark, not merely
    unlinked — an unlinked page is still crawlable and shareable."""
    # Asserted as behaviour in both directions below. A bare `FEATURES["phrase_search"] is False`
    # here would veto the feature's own release — it turns red on the deliberate flip, for a reason
    # that has nothing to do with the gating this test exists to lock. The shipped value is a release
    # decision, recorded in test_wave0.DELIBERATELY_RELEASED.
    before = config.FEATURES.get("phrase_search")
    try:
        config.FEATURES["phrase_search"] = False
        assert "phrases/search.html" not in _nav_html()
        config.FEATURES["phrase_search"] = True
        assert "phrases/search.html" in _nav_html()
    finally:
        config.FEATURES["phrase_search"] = before


def _nav_html() -> str:
    return site.page("t", "<p>body</p>", depth=0)


def test_one_malformed_phrase_json_cannot_crash_the_whole_build():
    """R-F (docs/23 §7.5 amendment 3). The phrase-PAGE loop skips a non-dict JSON; the index called
    .get() on whatever deserialized, so a single list/scalar file raised AttributeError out of
    build_site and took down every page — the entire site, not one row. The guards must agree."""
    import tempfile
    from pipeline import privacy  # noqa: F401  (index consults it; import must stay live)

    before = site.DERIVED
    with tempfile.TemporaryDirectory() as td:
        pdir = Path(td) / "phrases"
        pdir.mkdir()
        (pdir / "aaa_list.json").write_text("[1, 2, 3]", encoding="utf-8")   # a list
        (pdir / "bbb_str.json").write_text('"just a string"', encoding="utf-8")
        (pdir / "ccc_num.json").write_text("42", encoding="utf-8")
        (pdir / "ddd_ok.json").write_text(
            json.dumps({"ngram": "rule of law", "slug": "ddd_ok", "peak_units": 7,
                        "first_seen": {"date": "2026-01-03"},
                        "series": [{"day": "2026-01-03", "D": 7, "R": 0, "I": 0}]}),
            encoding="utf-8")
        try:
            site.DERIVED = Path(td)
            rows = site.phrase_search_index()          # must not raise
        finally:
            site.DERIVED = before
    # the malformed files are skipped one-for-one; the good phrase still indexes
    assert [r["q"] for r in rows] == ["rule of law"], rows


def test_disclosure_states_what_the_index_does_not_cover():
    """The index is phrases-with-pages, not the 2.8M-ngram ledger. A reader searching a phrase and
    finding nothing must learn that it never cleared the tracking bar — not conclude nobody said it."""
    body = site.phrase_search_body(_ROWS)
    assert "not the full n-gram ledger" in body
    assert "three members" in body
