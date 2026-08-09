"""S66-2 acceptance: no render turns a poisoned citation URL into an attribute breakout.

docs/39 H4. site.py `_concordance_column` interpolated the citation URL straight into an href
while every sibling receipt path escaped it. The scheme whitelist in `_safe_http_url` stops
`javascript:` and `data:`, and stops nothing else: an `https://` URL carrying a double quote
closes the attribute and the rest becomes markup on a site that advertises zero JavaScript.
The corpus is external and mirrorable, so the URL is attacker-reachable input.

The defect was latent because the Concordance is dark. That is exactly why it is tested here:
the flip is the release act, and a flip is a bad moment to discover an escaping hole. Every
dark render is covered, plus one live render as a control, so the next dark surface inherits
the check instead of rediscovering the incident.
"""
from __future__ import annotations

from pipeline import config, site


# Passes the http(s) scheme whitelist, then closes the attribute and opens an event handler.
POISON = 'https://evil.example/x" onmouseover="alert(1)'
POISON_ESCAPED = "https://evil.example/x&quot; onmouseover=&quot;alert(1)"


def assert_no_attribute_breakout(html: str, *, label: str) -> None:
    assert POISON not in html, f"{label}: the raw poisoned URL reached the page"
    assert 'onmouseover="' not in html, f"{label}: a live event handler attribute was emitted"
    assert 'onmouseover=' not in html.replace(POISON_ESCAPED, ""), f"{label}: unescaped handler"


def _cdata() -> dict:
    return {"members": [{"bioguide": "A", "name": "Rep. Alice", "party": "D", "state": "CA",
                         "chamber": "house", "statements": 10, "on_script": 4, "index": 0.4,
                         "receipts": [{"phrase": "protect social security benefits",
                                       "date": "2026-06-01", "url": POISON}]}],
            "window": {"start": "2026-06-01", "end": "2026-06-30"}, "min_statements": 10,
            "counts": {"named": 1, "excluded_below_floor": 5, "members_seen": 6},
            "peak_floor": 15, "nomenclature_index_version": "idx-119-abc", "span_gated": True}


def _duet_day() -> dict:
    def side(name, party, state):
        return [{"member": name, "party": party, "state": state, "date": "2026-06-30",
                 "url": POISON, "quote": f"That is a victory for the rule of law, said {name}."}]
    return {"duets": [{"ngram": "rule of law", "counts": {"D": 9, "R": 5}, "both": 5,
                       "sides": {"D": side("Dana Adams", "D", "CA"),
                                 "R": side("Rhea Rivera", "R", "TX")}}]}


def _adata() -> dict:
    return {"window": {"start": "2026-06-09", "end": "2026-06-15"}, "min_active": 15,
            "caucus": {"D": 200, "R": 200}, "nomenclature_index_version": "idx-119-abc",
            "span_gated": True,
            "unison": {"D": [{"ngram": POISON, "slug": POISON, "day": "2026-06-15",
                              "offices_using": 30, "offices_active": 40, "office_share": 0.75,
                              "members": [{"bioguide": "D1", "name": POISON, "state": "CA"}],
                              "members_more": 29}], "R": []},
            "void": {"available": False, "loudest_silence": None, "note": POISON}}


def _chapters() -> list[dict]:
    return [{"kind": "era", "congress": 119, "party": "D", "label": POISON, "id": POISON,
             "stats": {"statements": 100, "top_phrases": [
                 {"phrase": POISON, "peak_members": 30, "first_date": "2025-06-30"}]},
             "verifier": {"passed": True}},
            {"kind": "month", "congress": 119, "party": "R", "label": POISON, "id": POISON,
             "stats": {"statements": 80, "top_phrases": []}, "verifier": {"passed": True}}]


# --- dark renders --------------------------------------------------------------------------

def test_the_concordance_escapes_a_poisoned_citation_url():
    html = site.concordance_body(_cdata())
    assert_no_attribute_breakout(html, label="concordance")
    assert POISON_ESCAPED in html, "the receipt link stopped rendering instead of being escaped"


def test_the_duet_escapes_a_poisoned_citation_url():
    original = config.FEATURES.get("duet")
    try:
        config.FEATURES["duet"] = True
        html = site.duet_panel(_duet_day())
    finally:
        config.FEATURES["duet"] = original
    assert html, "the duet fixture rendered nothing, so the check proved nothing"
    assert_no_attribute_breakout(html, label="duet")


def test_the_awards_page_escapes_poisoned_strings():
    html = site.awards_body(_adata())
    assert html
    assert_no_attribute_breakout(html, label="awards")


def test_the_archive_index_escapes_a_poisoned_chapter_identity():
    html = site.archive_index_body(_chapters())
    assert html
    assert_no_attribute_breakout(html, label="archive")


# --- live render control -------------------------------------------------------------------

def test_the_live_phrase_evidence_render_escapes_a_poisoned_citation_url():
    day = "2026-06-30"
    record = {"peak_day": day, "grounded_units": 3, "counts": {"D": 3, "R": 0},
              "receipts": [{"member": f"Member {index}", "party": "D", "state": "CA",
                            "date": day, "url": POISON} for index in range(3)]}
    phrase = {"ngram": "rule of law", "slug": "control", "first_seen": {"date": day},
              "series": [{"day": day, "D": 3, "R": 0, "I": 0}]}
    html = site.phrase_evidence_body(phrase, evidence={"phrases": {"control": record}})
    assert html, "the control render produced nothing, so the check proved nothing"
    assert_no_attribute_breakout(html, label="phrase evidence")


# --- the rule, not the instance --------------------------------------------------------------

def test_every_citation_url_reaches_its_href_through_the_escaper():
    """A new render must not reintroduce the hole by copying the old line."""
    import re
    from pathlib import Path
    source = Path(site.__file__).read_text(encoding="utf-8")
    offenders = []
    for number, line in enumerate(source.splitlines(), 1):
        for match in re.finditer(r'href="\{([^}]*)\}', line):
            expression = match.group(1)
            if "url" in expression.lower() and not expression.startswith("esc("):
                offenders.append((number, line.strip()[:90]))
    assert not offenders, offenders
