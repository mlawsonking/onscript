"""W2-B: deterministic discovery surfaces for the public static site."""
from __future__ import annotations

import json
import re
import tempfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

from pipeline import config, site


ATOM = "{http://www.w3.org/2005/Atom}"


def _day(day: str, i: int) -> dict:
    return {
        "day": day,
        "daily_lines": {
            "D": {"composite": f"PRIVATE COMPOSITE D {i}", "generator": "deterministic"},
            "R": {"composite": f"PRIVATE COMPOSITE R {i}", "generator": "deterministic"},
        },
        "top_synchronized": [
            {"ngram": f"computed phrase d {i}", "party": "D", "day_peak": 3,
             "first_seen": {"date": day}},
            *([{"ngram": f"computed phrase r {i}", "party": "R", "day_peak": 4,
                "first_seen": {"date": day}}] if i % 2 else []),
        ],
    }


def _build(n: int = 32) -> tuple[Path, list[str]]:
    tmp = Path(tempfile.mkdtemp(prefix="onscript-distribution-"))
    derived, out = tmp / "derived", tmp / "public"
    (derived / "days").mkdir(parents=True)
    days = []
    start = date(2026, 1, 1)
    for i in range(n):
        day = (start + timedelta(days=i)).isoformat()
        days.append(day)
        (derived / "days" / f"{day}.json").write_text(json.dumps(_day(day, i)), encoding="utf-8")
    saved = (site.DERIVED, site.OUT, config.DERIVED)
    try:
        site.DERIVED, site.OUT, config.DERIVED = derived, out, derived
        site.build_site()
    finally:
        site.DERIVED, site.OUT, config.DERIVED = saved
    return out, days


def test_atom_feed_matches_the_last_thirty_published_day_pages():
    out, days = _build()
    root = ET.parse(out / "feed.xml").getroot()
    entries = root.findall(f"{ATOM}entry")
    ids = [e.findtext(f"{ATOM}id") for e in entries]
    expected = [f"{config.SITE_URL}/day/{d}.html" for d in reversed(days[-30:])]
    assert ids == expected
    assert root.findtext(f"{ATOM}updated") == f"{days[-1]}T00:00:00Z"
    assert root.findtext(f"{ATOM}author/{ATOM}name") == "OnScript"


def test_feed_entries_are_symmetric_code_computed_summaries_without_prose():
    out, _ = _build(3)
    feed = (out / "feed.xml").read_text(encoding="utf-8")
    assert "PRIVATE COMPOSITE" not in feed
    assert "computed phrase" not in feed
    root = ET.fromstring(feed)
    for entry in root.findall(f"{ATOM}entry"):
        summary = entry.findtext(f"{ATOM}summary") or ""
        assert re.fullmatch(
            r"Democrats: \d+ synchronized phrases; Republicans: \d+ synchronized phrases\.", summary)
        day = (entry.findtext(f"{ATOM}id") or "").removesuffix(".html").rsplit("/", 1)[-1]
        assert entry.findtext(f"{ATOM}updated") == f"{day}T00:00:00Z"


def test_feed_builder_has_no_path_to_composite_or_statement_text():
    """Privacy-shaped source guard: future refactors cannot quietly source entry copy from prose."""
    import ast
    import inspect
    import textwrap

    fn = ast.parse(textwrap.dedent(inspect.getsource(site.atom_feed))).body[0]
    referenced = {n.value for n in ast.walk(fn)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    referenced |= {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
    assert not ({"daily_lines", "composite", "statement", "statements", "text"} & referenced)


def test_sitemap_is_exactly_the_rendered_html_page_set():
    out, _ = _build(3)
    root = ET.parse(out / "sitemap.xml").getroot()
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    got = {u.findtext(f"{ns}loc") for u in root.findall(f"{ns}url")}
    expected = {
        f"{config.SITE_URL}/" if p.relative_to(out).as_posix() == "index.html"
        else f"{config.SITE_URL}/{p.relative_to(out).as_posix()}"
        for p in out.rglob("*.html")
        if p.relative_to(out).as_posix() != "404.html"
    }
    assert got == expected
    assert f"{config.SITE_URL}/404.html" not in got


def test_robots_alternate_links_and_public_copy_point_to_the_feed():
    out, _ = _build(2)
    assert (out / "robots.txt").read_text(encoding="utf-8") == (
        f"User-agent: *\nAllow: /\nSitemap: {config.SITE_URL}/sitemap.xml\n")
    alternate = (f'<link rel="alternate" type="application/atom+xml" title="OnScript daily feed" '
                 f'href="{config.SITE_URL}/feed.xml">')
    for page in out.rglob("*.html"):
        assert alternate in page.read_text(encoding="utf-8"), page
    for name in ("about.html", "methodology.html"):
        html = (out / name).read_text(encoding="utf-8")
        assert 'href="feed.xml"' in html and "Atom feed" in html
