"""W2-C: mechanical accessibility, fallback, favicon, and internal-link guards."""
from __future__ import annotations

import ast
import json
import re
import tempfile
import textwrap
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pipeline import config, site


DAY = "2026-03-04"
SLUG = "accessible-phrase"


def _build() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="onscript-a11y-"))
    derived, out = tmp / "derived", tmp / "public"
    (derived / "days").mkdir(parents=True)
    (derived / "phrases").mkdir(parents=True)
    day = {
        "day": DAY,
        "daily_lines": {p: {"composite": f"{p} fixture.", "generator": "deterministic"}
                        for p in ("D", "R")},
        "top_synchronized": [{"ngram": "accessible public phrase", "slug": SLUG, "party": "D",
                              "day_peak": 5, "counts": {"D": 5, "R": 2},
                              "series": [1, 3, 5], "first_seen": {"date": "2026-03-02"}}],
    }
    phrase = {
        "ngram": "accessible public phrase", "slug": SLUG,
        "first_seen": {"date": "2026-03-02", "bioguide": "A000001"},
        "series": [{"day": "2026-03-02", "D": 1, "R": 0},
                   {"day": "2026-03-03", "D": 3, "R": 1},
                   {"day": DAY, "D": 5, "R": 2}],
    }
    (derived / "days" / f"{DAY}.json").write_text(json.dumps(day), encoding="utf-8")
    (derived / "phrases" / f"{SLUG}.json").write_text(json.dumps(phrase), encoding="utf-8")
    (derived / "phrases" / "top.json").write_text(
        json.dumps({"day": DAY, "by_peak": day["top_synchronized"], "by_velocity": []}),
        encoding="utf-8")
    saved = (site.DERIVED, site.OUT, config.DERIVED)
    try:
        site.DERIVED, site.OUT, config.DERIVED = derived, out, derived
        site.build_site()
    finally:
        site.DERIVED, site.OUT, config.DERIVED = saved
    return out


def test_every_page_has_language_skip_link_and_exactly_one_landmark_set():
    out = _build()
    for page in out.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert '<html lang="en">' in html, page
        assert html.count('<main id="main-content">') == 1, page
        assert html.count("</main>") == 1, page
        assert html.count('<header class="site">') == 1, page
        assert html.count('<nav class="top"') == 1, page
        assert html.count('<footer class="site">') == 1, page
        assert '<a class="skip-link" href="#main-content">Skip to main content</a>' in html, page


def test_every_inline_svg_has_role_title_and_description():
    out = _build()
    svgs = []
    for page in out.rglob("*.html"):
        svgs.extend(re.findall(r"<svg\b.*?</svg>", page.read_text(encoding="utf-8"), re.S))
    assert svgs
    for svg in svgs:
        assert 'role="img"' in svg
        assert re.search(r"<title>[^<]+</title>", svg)
        assert re.search(r"<desc>[^<]+</desc>", svg)


def test_svg_builders_cannot_read_composite_or_statement_prose():
    import inspect

    for builder in (site.sparkline_svg, site.curve_svg):
        fn = ast.parse(textwrap.dedent(inspect.getsource(builder))).body[0]
        referenced = {n.value for n in ast.walk(fn)
                      if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        referenced |= {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
        assert not ({"daily_lines", "composite", "statement", "statements", "text"} & referenced)


def test_404_and_favicon_are_built_from_the_committed_brand_asset():
    out = _build()
    assert (out / "404.html").exists()
    source = config.REPO_ROOT / "site" / "brand" / "avatar-brand.png"
    assert (out / "favicon.png").read_bytes() == source.read_bytes()
    for page in out.rglob("*.html"):
        rel = "../" * len(page.relative_to(out).parent.parts)
        assert f'<link rel="icon" type="image/png" href="{rel}favicon.png">' in page.read_text(encoding="utf-8")


def test_phrase_peak_date_links_to_its_existing_day_page():
    out = _build()
    html = (out / "phrases" / f"{SLUG}.html").read_text(encoding="utf-8")
    assert f'href="../day/{DAY}.html">{DAY}</a>' in html


def test_every_relative_internal_link_resolves_inside_the_built_site():
    out = _build()
    failures = []
    for page in out.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        for href in re.findall(r'<a\b[^>]*\bhref="([^"]+)"', html):
            split = urlsplit(href)
            if split.scheme or split.netloc or not split.path:
                continue
            target = (page.parent / unquote(split.path)).resolve()
            if not target.exists() or out.resolve() not in target.parents:
                failures.append((page.relative_to(out).as_posix(), href))
    assert failures == []
