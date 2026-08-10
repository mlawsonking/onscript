"""S67-6 and S67-7a: phrase-index clarity, and the essays surface that is unwritten while empty.

The clarity half closes three things a reader could not resolve from the page: what Velocity is,
why two per-party tables have different row counts, and why a heading reads "1 8 billion". The
essays half is the P1 blocking dependency, built on the posts.html rule and one notch stricter:
zero essays is zero bytes, not an empty index waiting to be shared.
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from pipeline import build, config, public_strings, site


DAY = "2026-07-02"
SLUG = "clarity-phrase"
NGRAM = "1 8 billion"


def _build(*, essays_dir: Path | None = None, surfaces: dict | None = None) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="onscript-s67-clarity-"))
    derived, out = tmp / "derived", tmp / "public"
    (derived / "days").mkdir(parents=True)
    (derived / "phrases").mkdir(parents=True)
    row = {"ngram": NGRAM, "slug": SLUG, "party": "D", "day_peak": 9, "velocity": 4.5,
           "counts": {"D": 9, "R": 2}, "series": [1, 4, 9], "first_seen": {"date": "2026-06-30"}}
    (derived / "days" / f"{DAY}.json").write_text(json.dumps({
        "day": DAY,
        "daily_lines": {p: {"composite": f"{p} line.", "generator": "deterministic"}
                        for p in ("D", "R")},
        "top_synchronized": [row],
        "sync_by_party": {"D": [row], "R": []},
    }), encoding="utf-8")
    (derived / "phrases" / f"{SLUG}.json").write_text(json.dumps({
        "slug": SLUG, "ngram": NGRAM, "first_seen": {"date": "2026-06-30"},
        "series": [{"day": "2026-06-30", "D": 1, "R": 0}, {"day": "2026-07-01", "D": 4, "R": 1},
                   {"day": DAY, "D": 9, "R": 2}]}), encoding="utf-8")
    (derived / "phrases" / "top.json").write_text(json.dumps(
        {"day": DAY, "by_peak": [row], "by_velocity": [row]}), encoding="utf-8")
    if surfaces is not None:
        (derived / "phrase-surfaces.json").write_text(json.dumps(
            {"method_version": "probe", "surfaces": surfaces}), encoding="utf-8")
    saved = (site.DERIVED, site.OUT, config.DERIVED, site.ESSAYS, site.HAS_ESSAYS,
             site.ESSAYS_DIR, site.PHRASE_SURFACES)
    try:
        site.DERIVED, site.OUT, config.DERIVED = derived, out, derived
        site.PHRASE_SURFACES = surfaces or {}
        if essays_dir is not None:
            site.ESSAYS_DIR = essays_dir
        site.ESSAYS = site.load_essays()
        site.HAS_ESSAYS = bool(site.ESSAYS)
        site.build_site()
    finally:
        (site.DERIVED, site.OUT, config.DERIVED, site.ESSAYS, site.HAS_ESSAYS,
         site.ESSAYS_DIR, site.PHRASE_SURFACES) = saved
    return out


# --- S67-6 clarity --------------------------------------------------------------------------

def test_velocity_is_defined_where_the_column_is_shown():
    html = (_build() / "phrases" / "index.html").read_text(encoding="utf-8")
    assert "Velocity</th>" in html
    assert site.esc(public_strings.VELOCITY_DEFINITION) in html
    assert html.index("Velocity</th>") < html.index(site.esc(public_strings.VELOCITY_DEFINITION))


def test_the_velocity_sentence_matches_its_owning_calculation():
    """The definition is prose about pipeline/build._velocity, so it has to describe THAT: the
    day's count over the mean of the prior 14 present days, not a percentage or a rate."""
    doc = build._velocity.__doc__
    assert "14" in doc and "mean" in doc
    text = public_strings.VELOCITY_DEFINITION
    assert "14 days" in text and "divided by" in text and "average" in text
    daily = {"2026-06-%02d" % d: {"D": 2, "R": 0} for d in range(1, 15)}
    daily[DAY] = {"D": 4, "R": 0}
    assert build._velocity(daily, DAY) == 2.0, "the sentence describes a ratio; so must the code"


def test_the_party_imbalance_note_sits_under_both_repeated_phrase_surfaces():
    out = _build()
    note = site.esc(public_strings.PARTY_IMBALANCE_NOTE)
    for relative in ("index.html", "phrases/index.html"):
        html = (out / relative).read_text(encoding="utf-8")
        assert note in html, relative
        assert "symmetry audit</a>" in html, relative


def test_the_imbalance_note_points_at_where_source_volume_is_measured():
    text = public_strings.PARTY_IMBALANCE_NOTE.lower()
    assert "not comparable" in text
    assert "symmetry audit" in text


def test_the_phrase_page_shows_a_surface_form_beside_the_normalized_key():
    out = _build(surfaces={SLUG: "1.8 billion"})
    html = (out / "phrases" / f"{SLUG}.html").read_text(encoding="utf-8")
    assert f"<h1>&ldquo;{NGRAM}&rdquo;</h1>" in html, "the normalized key remains the identity"
    assert "1.8 billion" in html
    assert public_strings.SURFACE_FORM_LABEL in html
    assert f"Normalized key: {NGRAM}" in html
    assert 'class="normkey"' in html


def test_a_phrase_with_no_surface_on_record_simply_omits_the_line():
    """The artifact is absent on every deployment until its builder has run in production, and
    that must render exactly the page that shipped yesterday."""
    html = (_build() / "phrases" / f"{SLUG}.html").read_text(encoding="utf-8")
    assert public_strings.SURFACE_FORM_LABEL not in html
    assert f"<h1>&ldquo;{NGRAM}&rdquo;</h1>" in html


def test_the_surface_picker_is_deterministic_and_counts_one_unit_once():
    from pipeline import phrase_evidence as pe
    assert pe._surface_forms("1 8 billion", "We secured $1.8 billion today.") == ["1.8 billion"]
    assert pe._surface_forms("1 8 billion", "nothing here") == []
    # Most frequent wins; ties go to the lexicographically first spelling.
    from collections import Counter
    counts = Counter({"1.8 Billion": 2, "1.8 billion": 2, "1-8-billion": 1})
    assert min(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0] == "1.8 Billion"


def test_the_evidence_slice_still_carries_no_statement_text():
    """The surface form is a source fragment, so it publishes through its OWN artifact and the
    metadata-only contract of phrase-evidence.json is untouched."""
    from pipeline import phrase_evidence as pe
    import inspect
    source = inspect.getsource(pe.build_phrase_evidence)
    assert 'k != "surface"' in source
    assert "phrase-surfaces.json" in source
    assert pe.SURFACE_REVISION in source or "SURFACE_REVISION" in source


def test_the_surface_revision_participates_in_the_cache_key():
    """Otherwise every entry already cached in production is served back with no surface in it
    and the artifact populates only for phrases whose peak day happened to move."""
    from pipeline import phrase_evidence as pe
    import inspect
    key_line = next(line for line in inspect.getsource(pe.build_phrase_evidence).splitlines()
                    if "key = " in line)
    assert "SURFACE_REVISION" in key_line


# --- S67-7a essays --------------------------------------------------------------------------

def _essay(slug="p1", date="2026-08-20"):
    return {
        "slug": slug, "title": "A Title", "date": date, "byline": "Michael King",
        "dek": "One line about the piece.",
        "labels": ["correlation-not-cause", "replication"],
        "body": ["## A heading", "A paragraph of the author's prose."],
        "receipts": [{"member": "A Member", "date": "2026-07-01",
                      "url": "https://example.house.gov/a", "note": "context"}],
        "provenance": {"finding": "S1.9"},
    }


def _with_essays(essays: list[dict]) -> Path:
    directory = Path(tempfile.mkdtemp(prefix="onscript-s67-essays-"))
    for essay in essays:
        (directory / f"{essay['slug']}.json").write_text(json.dumps(essay), encoding="utf-8")
    return _build(essays_dir=directory)


def test_zero_essays_means_zero_bytes_and_no_nav_link():
    """An empty index is worse than no index: it is a promise with nothing behind it, and it gets
    crawled, shared and cached in that state."""
    out = _with_essays([])
    assert not (out / "essays").exists()
    for page in out.rglob("*.html"):
        assert "essays/index.html" not in page.read_text(encoding="utf-8"), page
    assert "essays" not in (out / "sitemap.xml").read_text(encoding="utf-8")


def test_one_essay_turns_the_surface_on_with_no_flag_to_flip():
    out = _with_essays([_essay()])
    assert (out / "essays" / "index.html").exists()
    assert (out / "essays" / "p1.html").exists()
    assert 'href="../essays/index.html">Essays</a>' in \
        (out / "day" / f"{DAY}.html").read_text(encoding="utf-8")
    assert "essays/p1.html" in (out / "sitemap.xml").read_text(encoding="utf-8")
    assert "essays" not in {k.lower() for k in config.FEATURES}


def test_an_essay_page_carries_byline_date_labels_and_receipts():
    out = _with_essays([_essay()])
    html = (out / "essays" / "p1.html").read_text(encoding="utf-8")
    assert "By Michael King" in html and "2026-08-20" in html
    assert "correlation-not-cause" in html
    assert site.esc(public_strings.ESSAY_LABELS["correlation-not-cause"]) in html
    assert 'class="receipts"' in html and "https://example.house.gov/a" in html
    assert "<h2>Provenance</h2>" in html and "S1.9" in html
    assert site.esc(public_strings.ESSAY_STANDING_NOTE) in html


def test_the_essay_shell_is_the_same_head_nav_and_footer_as_every_other_page():
    out = _with_essays([_essay()])
    html = (out / "essays" / "p1.html").read_text(encoding="utf-8")
    assert '<nav class="top" aria-label="Primary">' in html
    assert '<footer class="site">' in html
    assert '<meta property="og:url" content="https://onscript.news/essays/p1.html">' in html
    assert "@media (prefers-color-scheme: dark)" in html


def test_the_index_lists_essays_newest_first():
    out = _with_essays([_essay("older", "2026-08-01"), _essay("newer", "2026-09-01")])
    html = (out / "essays" / "index.html").read_text(encoding="utf-8")
    assert html.index('href="newer.html"') < html.index('href="older.html"')


def test_authored_essay_fields_are_escaped_and_a_bad_url_is_dropped():
    """Essay JSON is written by hand, and a hand can type a script tag or a javascript: URL."""
    essay = _essay()
    essay["title"] = '<script>alert(1)</script>'
    essay["body"] = ['<img src=x onerror=alert(1)>']
    essay["receipts"] = [{"member": "M", "date": "2026-07-01", "url": "javascript:alert(1)"}]
    out = _with_essays([essay])
    html = (out / "essays" / "p1.html").read_text(encoding="utf-8")
    # The payloads survive as TEXT (escaped) and never as markup: no new element, no attribute.
    assert "<script>alert(1)</script>" not in html
    assert "<img" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "javascript:" not in html
    assert (out / "essays" / "index.html").read_text(encoding="utf-8").count("<script") == \
        (out / "index.html").read_text(encoding="utf-8").count("<script")


def test_a_malformed_essay_file_is_skipped_rather_than_crashing_the_render():
    directory = Path(tempfile.mkdtemp(prefix="onscript-s67-badessay-"))
    (directory / "broken.json").write_text("[1, 2, 3]", encoding="utf-8")
    (directory / "untitled.json").write_text(json.dumps({"date": "2026-08-01"}), encoding="utf-8")
    out = _build(essays_dir=directory)
    assert not (out / "essays").exists()
    assert (out / "index.html").exists()
