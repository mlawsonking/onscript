"""S67-1 and S67-4: the front door, progressive disclosure, findability, and contact.

docs/39 graded distribution F: three weeks public, about two human followers, no analytics, no
contact address, the exports page unlinked, the feeds exposed only as <link rel> headers a reader
never sees. Every assertion here is one of those holes, closed and pinned, plus the reading-order
change that puts a sentence a stranger can understand above the first denominator.
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from pipeline import config, public_strings, site


DAY = "2026-05-12"
PREV = "2026-05-11"
SLUG = "front-door-phrase"


def _series(base: int):
    return [{"day": d, "D": v, "R": max(0, v - 2)}
            for d, v in zip(("2026-05-08", "2026-05-09", "2026-05-10", PREV, DAY),
                            (2, 6, 12, 18, base))]


def _day(day: str) -> dict:
    return {
        "day": day,
        "daily_lines": {p: {"composite": f"{p} fixture line.", "generator": "deterministic"}
                        for p in ("D", "R")},
        "top_synchronized": [{"ngram": "front door phrase", "slug": SLUG, "party": "D",
                              "day_peak": 20, "counts": {"D": 20, "R": 4},
                              "series": [2, 6, 12, 18, 20], "first_seen": {"date": "2026-05-08"}}],
        "participation": {
            p: {"measures": {
                "office_participation": {
                    "label": "Office participation", "numerator": 20, "numerator_unit": "offices",
                    "denominator": 213, "denominator_unit": "eligible caucus offices",
                    "window": day, "method_version": "participation-v1"},
                "publication_participation": {
                    "label": "Publication participation", "numerator": 24,
                    "numerator_unit": "publications", "denominator": 96,
                    "denominator_unit": "source publications", "window": day,
                    "method_version": "participation-v1"},
            }} for p in ("D", "R")},
    }


def _build(*, contact: str | None = None) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="onscript-s67-front-"))
    derived, out = tmp / "derived", tmp / "public"
    (derived / "days").mkdir(parents=True)
    (derived / "phrases").mkdir(parents=True)
    for day in (PREV, DAY):
        (derived / "days" / f"{day}.json").write_text(json.dumps(_day(day)), encoding="utf-8")
    (derived / "phrases" / f"{SLUG}.json").write_text(json.dumps({
        "ngram": "front door phrase", "slug": SLUG,
        "first_seen": {"date": "2026-05-08", "bioguide": "A000001"},
        "series": _series(20)}), encoding="utf-8")
    (derived / "phrases" / "top.json").write_text(json.dumps(
        {"day": DAY, "by_peak": _day(DAY)["top_synchronized"], "by_velocity": []}), encoding="utf-8")
    saved = (site.DERIVED, site.OUT, config.DERIVED, config.CONTACT_EMAIL)
    try:
        site.DERIVED, site.OUT, config.DERIVED = derived, out, derived
        if contact is not None:
            config.CONTACT_EMAIL = contact
        site.build_site()
    finally:
        site.DERIVED, site.OUT, config.DERIVED, config.CONTACT_EMAIL = saved
    return out


def _pages(out: Path):
    return sorted(out.rglob("*.html"))


# --- the front door -------------------------------------------------------------------------

def test_the_homepage_opens_with_one_plain_sentence_above_everything_else():
    """The sentence must precede the heading, the status header AND the first banner: a stranger
    who has to scroll past a temporal-state ladder to learn what the site is has already left."""
    html = (_build() / "index.html").read_text(encoding="utf-8")
    body = html.split('<main id="main-content">', 1)[1]
    door = body.index(public_strings.FRONT_DOOR)
    for later in ("<h1>", 'class="banner', "instrument-status"):
        assert later not in body[:door], f"{later!r} appears above the front-door sentence"


def test_the_front_door_links_methodology_and_about_in_one_line():
    html = (_build() / "index.html").read_text(encoding="utf-8")
    line = re.search(r'<p class="frontdoor-links">(.*?)</p>', html, re.S).group(1)
    assert 'href="methodology.html"' in line and 'href="about.html"' in line


def test_the_front_door_is_not_repeated_on_every_dated_day_page():
    out = _build()
    assert public_strings.FRONT_DOOR not in (out / "day" / f"{PREV}.html").read_text(encoding="utf-8")


def test_the_front_door_sentence_uses_no_jargon():
    """A front door written in the vocabulary of the methodology page is not a front door."""
    jargon = ("lane", "composite", "denominator", "n-gram", "corpus", "unit key", "quorum",
              "distilled", "epoch")
    lowered = public_strings.FRONT_DOOR.lower()
    assert not [w for w in jargon if w in lowered]


# --- progressive disclosure -----------------------------------------------------------------

def test_the_method_blocks_are_collapsed_and_sit_below_the_composites():
    html = (_build() / "index.html").read_text(encoding="utf-8")
    for name in ("participation", "class-lanes"):
        assert f'<details class="method" data-disclosure="{name}">' in html, name
    # Collapsed means no `open` attribute: a <details open> is a heading with extra steps.
    assert "<details class=\"method\" open" not in html
    assert '<div class="lines">' in html
    assert html.index('<div class="lines">') < html.index('<details class="method"')


def test_each_disclosure_summary_is_plain_english():
    html = (_build() / "index.html").read_text(encoding="utf-8")
    summaries = re.findall(r"<summary>([^<]+)</summary>", html)
    assert public_strings.DISCLOSURE_PARTICIPATION in summaries
    assert public_strings.DISCLOSURE_CLASS_LANES in summaries
    for text in summaries:
        assert text[0].isupper() and len(text.split()) <= 6, text


def test_the_participation_tables_still_carry_every_number_they_carried_before():
    """Collapsing moved the block; it may not have thinned it."""
    body = site.participation_panel(_day(DAY))
    for token in ("20 offices", "213 eligible caucus offices", "24 publications",
                  "96 source publications", "participation-v1"):
        assert token in body, token


def test_adjacent_denominators_say_they_are_different_bases():
    """The note has to sit where the two bases touch, not on a methodology page nobody opens."""
    body = site.participation_panel(_day(DAY))
    rendered = site.esc(public_strings.DENOMINATOR_BASES_NOTE)
    assert rendered in body
    assert body.index("eligible caucus offices") < body.index(rendered)
    assert body.index("source publications") < body.index(rendered)
    note = public_strings.DENOMINATOR_BASES_NOTE.lower()
    assert "differ" in note and "joint release" in note


def test_the_two_s66_honesty_strings_are_untouched():
    """S67 was a polish order, not a copy edit of the honesty notes."""
    assert public_strings.HOMEPAGE_HONESTY_NOTE.startswith("Honesty note: when a day's verified")
    assert public_strings.LANE_TWO_POPULATION_NOTE.startswith("Lane 2 is not currently populated")


# --- findability ----------------------------------------------------------------------------

def test_every_page_links_the_data_page_from_the_nav():
    out = _build()
    for page in _pages(out):
        rel = "../" * len(page.relative_to(out).parent.parts)
        html = page.read_text(encoding="utf-8")
        assert f'<a href="{rel}api/index.html">Data</a>' in html, page


def test_the_data_page_is_titled_data_and_api():
    html = (_build() / "api" / "index.html").read_text(encoding="utf-8")
    assert "<h1>Data and API</h1>" in html
    assert "<title>OnScript · Data and API</title>" in html


def test_every_footer_carries_visible_links_to_all_three_feeds():
    out = _build()
    for page in _pages(out):
        rel = "../" * len(page.relative_to(out).parent.parts)
        footer = page.read_text(encoding="utf-8").split('<footer class="site">', 1)[1]
        for feed in ("feed.xml", "corrections/feed.xml", "alerts/feed.xml"):
            assert f'href="{rel}{feed}"' in footer, f"{page}: {feed} not linked in the footer"


def test_the_sitemap_and_robots_cover_the_new_surfaces_consistently():
    out = _build()
    sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
    assert f"{config.SITE_URL}/api/index.html" in sitemap
    robots = (out / "robots.txt").read_text(encoding="utf-8")
    assert "Allow: /" in robots and f"Sitemap: {config.SITE_URL}/sitemap.xml" in robots
    # Nothing newly written may be missing from the sitemap: it is built from `written`, so a page
    # appended without its path would silently leave the map.
    for page in _pages(out):
        rel = page.relative_to(out).as_posix()
        # 404.html is deliberately excluded by sitemap(); unlisted working surfaces are named in
        # robots.txt instead of the map. Everything else must appear.
        if rel == "404.html" or rel.startswith("annotation"):
            continue
        assert rel in sitemap or f"/{rel}" in sitemap, f"{rel} is not in the sitemap"


# --- contact --------------------------------------------------------------------------------

def test_about_renders_the_contact_line_when_the_constant_is_set():
    html = (_build(contact="probe@onscript.news") / "about.html").read_text(encoding="utf-8")
    assert "mailto:probe@onscript.news" in html


def test_about_drops_the_contact_line_when_the_constant_is_empty():
    """The constant IS the switch. No flag, no template branch, no second place to look."""
    html = (_build(contact="") / "about.html").read_text(encoding="utf-8")
    assert "mailto:" not in html


def test_the_contact_constant_is_a_plain_string_and_not_a_feature_flag():
    assert isinstance(config.CONTACT_EMAIL, str)
    assert "contact" not in {k.lower() for k in config.FEATURES}


# --- analytics ------------------------------------------------------------------------------

ANALYTICS = '<script defer src="/_vercel/insights/script.js"></script>'


def test_the_analytics_line_is_on_every_page_exactly_once_and_is_same_origin():
    out = _build()
    for page in _pages(out):
        html = page.read_text(encoding="utf-8")
        assert html.count(ANALYTICS) == 1, page
    src = re.search(r'src="([^"]+)"', ANALYTICS).group(1)
    assert src.startswith("/") and not src.startswith("//"), (
        f"the analytics src must be a same-origin path, got {src!r}")
    assert "://" not in src, "no third-party host may appear in the analytics src"


def test_the_site_discloses_the_visit_counting_it_now_does():
    """Article XVII. The footer used to promise 'No tracking and no external requests'; the site
    now loads a counter, so the site now says so, in the footer and on About."""
    out = _build()
    about = (out / "about.html").read_text(encoding="utf-8")
    assert public_strings.ANALYTICS_DISCLOSURE in about
    for page in _pages(out):
        html = page.read_text(encoding="utf-8")
        assert public_strings.ANALYTICS_DISCLOSURE in html, page
        assert "No tracking and no external requests" not in html, page
    source = Path(site.__file__).read_text(encoding="utf-8")
    assert "no CDNs/web-fonts/analytics" not in source, (
        "the module docstring still claims the site loads no analytics")


def test_the_disclosure_names_what_is_and_is_not_collected():
    text = public_strings.ANALYTICS_DISCLOSURE.lower()
    assert "aggregate" in text and "cookie" in text
    assert "no identifier" in text
