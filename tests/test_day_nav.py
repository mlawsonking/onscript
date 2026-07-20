"""Day navigation (docs/23 §7.3 pre-launch duty).

The day pages were always written and always permanent — and were UNREACHABLE. index.html linked to
zero of them, and the prev/next chain between day pages therefore had no entry point: a published day
could only be found by typing its URL. These tests lock the correspondence that fixes it:

  * every published day has a page, AND that page is listed in the /day/ archive (no orphans);
  * the archive lists nothing that lacks a page (no 404s);
  * the homepage links into the chain (previous day) and to the archive.

This is navigation to already-public pages, so it is NOT behind a FEATURES flag — the last test
locks that too, so a later session can't quietly gate the table of contents.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, site  # noqa: E402


def _day(day, *, lines=True, sync=True):
    d = {"day": day, "schema_version": 1}
    if lines:
        d["daily_lines"] = {p: {"composite": f"{p} composite for {day}.", "generator": "deterministic",
                                "talking_points": []} for p in ("D", "R")}
    if sync:
        d["top_synchronized"] = [{"ngram": "border security funding", "party": "D", "day_peak": 7,
                                  "members_D": 7, "members_R": 0, "first_seen": {"date": day}}]
    return d


def _build(days: dict) -> Path:
    """Render a whole site into a temp dir from the given {day: day_json} and return the out dir."""
    tmp = Path(tempfile.mkdtemp(prefix="onscript-daynav-"))
    derived, out = tmp / "derived", tmp / "public"
    (derived / "days").mkdir(parents=True)
    for day, data in days.items():
        (derived / "days" / f"{day}.json").write_text(json.dumps(data), encoding="utf-8")

    saved = (site.DERIVED, site.OUT, config.DERIVED)
    try:
        site.DERIVED, site.OUT, config.DERIVED = derived, out, derived
        site.build_site()
    finally:
        site.DERIVED, site.OUT, config.DERIVED = saved
    return out


DAYS = {"2026-07-14": _day("2026-07-14"),
        "2026-07-15": _day("2026-07-15"),
        "2026-07-16": _day("2026-07-16", lines=False),   # phrases-only day: still published
        "2026-07-17": _day("2026-07-17")}


# --- the locked correspondence ------------------------------------------------------------
def test_every_published_day_has_a_page_and_is_listed_in_the_archive():
    out = _build(DAYS)
    index = (out / "day" / "index.html").read_text(encoding="utf-8")
    for day in DAYS:
        assert (out / "day" / f"{day}.html").exists(), f"{day} published but has no page"
        assert f'href="{day}.html"' in index, f"{day} has a page but is not listed in /day/"


def test_the_archive_lists_no_page_that_does_not_exist():
    """The inverse guard: a listed day that 404s is worse than an unlisted one."""
    out = _build(DAYS)
    index = (out / "day" / "index.html").read_text(encoding="utf-8")
    import re
    for slug in re.findall(r'href="(\d{4}-\d{2}-\d{2})\.html"', index):
        assert (out / "day" / f"{slug}.html").exists(), f"archive links a missing page: {slug}"


def test_a_day_with_neither_lines_nor_phrases_is_neither_rendered_nor_listed():
    """A stub day must not appear in the archive — the §Session-7 (D) rule that prev/next may only
    reference days that actually get a page, now extended to the index."""
    days = dict(DAYS, **{"2026-07-18": {"day": "2026-07-18", "schema_version": 1}})
    out = _build(days)
    assert not (out / "day" / "2026-07-18.html").exists()
    assert "2026-07-18.html" not in (out / "day" / "index.html").read_text(encoding="utf-8")


# --- the entry point ----------------------------------------------------------------------
def test_the_homepage_links_into_the_day_chain_and_to_the_archive():
    out = _build(DAYS)
    home = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="day/index.html"' in home, "homepage does not link the date archive"
    # 07-17 is 'today'; the previous published day is 07-16 (phrases-only days count as published).
    assert 'href="day/2026-07-16.html"' in home, "homepage does not link the previously published day"


def test_the_archive_marks_days_that_carry_no_daily_lines_rather_than_hiding_them():
    out = _build(DAYS)
    index = (out / "day" / "index.html").read_text(encoding="utf-8")
    assert "phrases only" in index               # 07-16 disclosed, not dropped
    # newest first — compare the LINKS, not bare dates (the subhead carries the range "from X to Y")
    assert index.index('href="2026-07-17.html"') < index.index('href="2026-07-14.html"')


def test_a_single_day_site_still_renders_a_coherent_archive_and_homepage():
    """Day one of the streak: no previous day exists, so the homepage must not emit a broken link."""
    out = _build({"2026-07-17": _day("2026-07-17")})
    home = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="day/index.html"' in home
    assert 'href="day/2026-07-1' not in home.split('<nav')[-1].split('</nav>')[0]  # no phantom prev in nav
    assert "&larr;" not in home                                   # no dangling "previous day" arrow
    assert "1 day, from 2026-07-17 to 2026-07-17" in (out / "day" / "index.html").read_text(encoding="utf-8")


# --- it is navigation, not a feature ------------------------------------------------------
def test_the_date_archive_is_not_behind_a_features_flag():
    """Locked: the archive links pages that are ALREADY public. Gating it would be gating the table
    of contents of a book already on the shelf — and would re-orphan every day page."""
    assert 'day/index.html">Days</a>' in site.page("t", "<p>b</p>")
    for flag, on in config.FEATURES.items():
        assert on is False, f"FEATURES[{flag!r}] is not dark — this test asserts the archive needs no flag"
