"""S67-2: the adoption curves and the two homepage exemplar picks.

The chart is the one thing on the site that shows the instrument doing what it claims to do, so
three properties are pinned rather than eyeballed: the party distinction survives without color,
the picks are a pure function of the corpus (Article IV: neither party's pick constrains the
other's), and the bytes do not move between two renders of the same input (docs/37 rule 5).
"""
from __future__ import annotations

import ast
import inspect
import json
import re
import tempfile
import textwrap
from pathlib import Path

from pipeline import config, public_strings, site


def _rows(days, d_vals, r_vals):
    return [{"day": day, "D": d, "R": r} for day, d, r in zip(days, d_vals, r_vals)]


DAYS = [f"2026-06-{n:02d}" for n in range(1, 11)]
SERIES = _rows(DAYS, [1, 2, 4, 9, 20, 31, 24, 12, 6, 3], [0, 0, 1, 2, 3, 5, 4, 2, 1, 0])


def _record(slug, ngram, series, first_seen):
    return (slug, {"slug": slug, "ngram": ngram, "series": series,
                   "first_seen": {"date": first_seen}})


# --- the curve ------------------------------------------------------------------------------

def test_the_curve_carries_a_non_color_cue_for_each_party():
    """About one man in twelve cannot separate these two hues, and a screenshot in grayscale
    loses them for everyone. D is solid, R is dashed, and the legend says so in words."""
    svg = site.curve_svg(SERIES)
    r_line = re.search(r'<polyline[^>]*stroke="var\(--red\)"[^>]*>', svg).group(0)
    d_line = re.search(r'<polyline[^>]*stroke="var\(--blue\)"[^>]*>', svg).group(0)
    assert 'stroke-dasharray="6 4"' in r_line
    assert "stroke-dasharray" not in d_line
    legend = site._series_legend()
    assert "dashed line" in legend and "solid line" in legend
    assert "Democrats" in legend and "Republicans" in legend


def test_the_curve_names_its_axes_and_both_peaks_in_its_description():
    svg = site.curve_svg(SERIES)
    title = re.search(r"<title>([^<]+)</title>", svg).group(1)
    desc = re.search(r"<desc>([^<]+)</desc>", svg).group(1)
    assert "offices" in title and "party" in title
    assert "solid line" in desc and "dashed line" in desc
    assert "31" in desc and "5" in desc          # both parties' peaks are stated
    assert DAYS[0] in desc and DAYS[-1] in desc  # the horizontal extent is stated


def test_the_curve_is_legible_in_both_themes():
    """Every stroke and fill resolves through a stylesheet token, so the dark palette moves the
    chart with the page instead of leaving a black line on a black panel."""
    svg = site.curve_svg(SERIES)
    literals = re.findall(r'(?:stroke|fill)="(#[0-9a-fA-F]{3,6})"', svg)
    assert not literals, f"the curve hard-codes {literals}, which only has a light theme"


def test_the_curve_carries_no_prose_only_counts_and_dates():
    """The Atom and og: rule extends inside the SVG: <title>/<desc> are scraped and read aloud,
    and no publication audit scans them."""
    fn = ast.parse(textwrap.dedent(inspect.getsource(site.curve_svg))).body[0]
    referenced = {n.value for n in ast.walk(fn)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    referenced |= {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
    assert not ({"daily_lines", "composite", "statement", "statements", "text", "quote"}
                & referenced)
    svg = site.curve_svg(SERIES)
    assert "<script" not in svg


def test_two_renders_of_one_series_are_byte_identical():
    """No clock, no randomness, no dict-order dependence: the proof that a re-render of a
    published day cannot churn the commit."""
    assert site.curve_svg(SERIES) == site.curve_svg(json.loads(json.dumps(SERIES)))
    assert site.curve_svg(SERIES, width=440, height=190) == site.curve_svg(SERIES, width=440, height=190)


def test_the_curve_reads_no_clock():
    source = textwrap.dedent(inspect.getsource(site.curve_svg))
    for forbidden in ("datetime.now", "date.today", "time.time", "utcnow"):
        assert forbidden not in source, f"curve_svg reads a clock via {forbidden}"


# --- the exemplar picks ---------------------------------------------------------------------

def test_each_party_is_ranked_against_its_own_phrases_and_never_pooled():
    """The pooled top-20 measured 88 percent Democratic (#146). Ranking once and taking the top
    two publishes the larger caucus twice; each party gets its own ranking and its own slot."""
    floor = config.CONCORDANCE_PEAK_FLOOR
    records = [
        _record("dbig", "d big phrase", _rows(DAYS, [0] * 9 + [floor + 20], [0] * 10), "2026-06-01"),
        _record("dmid", "d mid phrase", _rows(DAYS, [0] * 9 + [floor + 5], [0] * 10), "2026-06-01"),
        _record("rone", "r only phrase", _rows(DAYS, [0] * 10, [0] * 9 + [floor + 1]), "2026-06-02"),
    ]
    picks = site.adoption_exemplars(records, DAYS[-1])
    assert picks["D"]["slug"] == "dbig"
    assert picks["R"]["slug"] == "rone", "R's panel must not be filled by a Democratic phrase"


def test_a_phrase_below_the_coordination_floor_never_wins_a_panel():
    floor = config.CONCORDANCE_PEAK_FLOOR
    records = [_record("low", "low phrase", _rows(DAYS, [0] * 9 + [floor - 1], [0] * 10), "2026-06-01")]
    assert site.adoption_exemplars(records, DAYS[-1])["D"] is None


def test_a_party_with_nothing_qualifying_gets_an_honest_empty_panel():
    """August recess is real. The bar does not move to fill a box."""
    floor = config.CONCORDANCE_PEAK_FLOOR
    records = [_record("d", "d phrase", _rows(DAYS, [0] * 9 + [floor + 2], [0] * 10), "2026-06-01")]
    html = site.adoption_exemplar_panel(site.adoption_exemplars(records, DAYS[-1]),
                                        slugs_with_pages={"d"})
    assert public_strings.ADOPTION_EMPTY_PANEL in html
    assert 'data-party="R"' in html and 'data-party="D"' in html


def test_the_window_excludes_a_peak_that_fell_out_of_it():
    floor = config.CONCORDANCE_PEAK_FLOOR
    old = [{"day": "2026-01-05", "D": floor + 40, "R": 0}] + _rows(DAYS, [1] * 10, [0] * 10)
    records = [_record("old", "old phrase", old, "2026-01-05")]
    assert site.adoption_exemplars(records, DAYS[-1], window_days=90)["D"] is None
    assert site.adoption_exemplars(records, DAYS[-1], window_days=365)["D"]["slug"] == "old"


def test_ties_break_on_first_seen_then_slug_and_never_on_dict_order():
    floor = config.CONCORDANCE_PEAK_FLOOR
    tied = _rows(DAYS, [0] * 9 + [floor + 3], [0] * 10)
    records = [_record("zebra", "zebra phrase", tied, "2026-06-01"),
               _record("alpha", "alpha phrase", tied, "2026-06-01"),
               _record("early", "early phrase", tied, "2026-05-30")]
    assert site.adoption_exemplars(records, DAYS[-1])["D"]["slug"] == "early"
    assert site.adoption_exemplars(list(reversed(records)), DAYS[-1])["D"]["slug"] == "early"
    no_early = [r for r in records if r[0] != "early"]
    assert site.adoption_exemplars(no_early, DAYS[-1])["D"]["slug"] == "alpha"
    assert site.adoption_exemplars(list(reversed(no_early)), DAYS[-1])["D"]["slug"] == "alpha"


def test_the_floor_is_read_from_its_owner_and_never_restated():
    """A second copy of a threshold is a threshold that drifts (docs/37 rule 1)."""
    source = textwrap.dedent(inspect.getsource(site.adoption_exemplars))
    assert "config.CONCORDANCE_PEAK_FLOOR" in source
    assert str(config.CONCORDANCE_PEAK_FLOOR) not in source
    original = config.CONCORDANCE_PEAK_FLOOR
    try:
        config.CONCORDANCE_PEAK_FLOOR = original + 100
        records = [_record("d", "d phrase", _rows(DAYS, [0] * 9 + [original + 2], [0] * 10),
                           "2026-06-01")]
        assert site.adoption_exemplars(records, DAYS[-1])["D"] is None
    finally:
        config.CONCORDANCE_PEAK_FLOOR = original


def test_the_printed_selection_rule_states_the_live_window_and_floor():
    floor = config.CONCORDANCE_PEAK_FLOOR
    records = [_record("d", "d phrase", _rows(DAYS, [0] * 9 + [floor + 2], [0] * 10), "2026-06-01")]
    html = site.adoption_exemplar_panel(site.adoption_exemplars(records, DAYS[-1]),
                                        slugs_with_pages={"d"})
    printed = re.search(r'<p class="selrule">(.*?)</p>', html, re.S).group(1)
    assert str(site.ADOPTION_WINDOW_DAYS) in printed and str(floor) in printed
    assert "Ties" in printed and "No model chooses" in printed


def test_a_suppressed_phrase_can_never_be_an_exemplar():
    """Article XIII at the selection gate, not only the render gate: this is the single most
    prominent chart on the site."""
    from pipeline import privacy
    original = privacy.is_suppressed
    floor = config.CONCORDANCE_PEAK_FLOOR
    try:
        privacy.is_suppressed = lambda text: "private" in str(text)
        records = [_record("p", "a private name phrase",
                           _rows(DAYS, [0] * 9 + [floor + 9], [0] * 10), "2026-06-01")]
        assert site.adoption_exemplars(records, DAYS[-1])["D"] is None
    finally:
        privacy.is_suppressed = original


def test_the_homepage_renders_both_panels_with_equal_weight():
    """Article IV in the markup: one grid, two identical cells. A wider party is a claim."""
    floor = config.CONCORDANCE_PEAK_FLOOR
    records = [_record("d", "d phrase", _rows(DAYS, [0] * 9 + [floor + 4], [0] * 10), "2026-06-01"),
               _record("r", "r phrase", _rows(DAYS, [0] * 10, [0] * 9 + [floor + 4]), "2026-06-01")]
    html = site.adoption_exemplar_panel(site.adoption_exemplars(records, DAYS[-1]),
                                        slugs_with_pages={"d", "r"})
    cells = re.findall(r'<div class="exemplar chartbox" data-party="([DR])"', html)
    assert cells == ["D", "R"]
    assert "grid-template-columns:1fr 1fr" in site.CSS
    assert html.count("<svg") == 2


def test_the_exemplar_panel_appears_on_the_homepage_below_the_composites():
    tmp = Path(tempfile.mkdtemp(prefix="onscript-s67-chart-"))
    derived, out = tmp / "derived", tmp / "public"
    (derived / "days").mkdir(parents=True)
    (derived / "phrases").mkdir(parents=True)
    floor = config.CONCORDANCE_PEAK_FLOOR
    day = DAYS[-1]
    (derived / "days" / f"{day}.json").write_text(json.dumps({
        "day": day,
        "daily_lines": {p: {"composite": f"{p} line.", "generator": "deterministic"}
                        for p in ("D", "R")},
        "top_synchronized": [],
    }), encoding="utf-8")
    for slug, party in (("d", "D"), ("r", "R")):
        vals = [0] * 9 + [floor + 4]
        series = _rows(DAYS, vals if party == "D" else [0] * 10,
                       vals if party == "R" else [0] * 10)
        (derived / "phrases" / f"{slug}.json").write_text(json.dumps(
            {"slug": slug, "ngram": f"{slug} phrase", "series": series,
             "first_seen": {"date": DAYS[0]}}), encoding="utf-8")
    saved = (site.DERIVED, site.OUT, config.DERIVED)
    try:
        site.DERIVED, site.OUT, config.DERIVED = derived, out, derived
        site.build_site()
    finally:
        site.DERIVED, site.OUT, config.DERIVED = saved
    html = (out / "index.html").read_text(encoding="utf-8")
    assert 'class="adoption-exemplars"' in html
    assert html.index('<div class="lines">') < html.index('class="adoption-exemplars"')
    # And nowhere else: a dated day page is an archive record, not a rolling window.
    assert 'class="adoption-exemplars"' not in (out / "day" / f"{day}.html").read_text(encoding="utf-8")
