"""Link cards — Open Graph meta on every page (docs/23 §7.5 amendment 2).

WHY THIS IS SITE CHROME AND NOT A FEATURE. Until now the site emitted zero og: tags, so every share of
it unfurled as a bare imageless URL: the launch announce, the receipts link carried in every composite
thread, and every reader's repost forever. That is the first impression of the whole project, and it is
decided by markup no reader ever sees — which is exactly why it needs locking rather than eyeballing.

The load-bearing test here is the og:url one. `path=` is passed by hand at 16 call sites, and a wrong
one produces a page that looks perfect and whose card points somewhere else. So og:url is checked
against each file's ACTUAL location on disk, for every file rendered — the one assertion a typo cannot
survive.

THE PRIVACY RULE, locked at the bottom: og values come from `page()`'s own title/description arguments
and never from composite prose. Composites pass `privacy_correct_line()`, which can withhold or
recompose them under Article XIII; a meta tag is a surface no audit scans and no reader sees, so
sourcing one from raw prose would republish precisely the text the page body withheld.
"""
import json
import re
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, site  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OG_PNG = REPO / "site" / "public" / "og.png"

_REQUIRED = ("og:type", "og:site_name", "og:title", "og:description", "og:url",
             "og:image", "og:image:width", "og:image:height", "og:image:alt")


def _day(day, *, lines=True):
    d = {"day": day, "schema_version": 1}
    if lines:
        d["daily_lines"] = {p: {"composite": f"{p} composite for {day}.", "generator": "deterministic",
                                "talking_points": []} for p in ("D", "R")}
    d["top_synchronized"] = [{"ngram": "border security funding", "party": "D", "day_peak": 7,
                              "members_D": 7, "members_R": 0, "first_seen": {"date": day}}]
    return d


def _build(days: dict) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="onscript-og-"))
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


DAYS = {"2026-07-16": _day("2026-07-16"), "2026-07-17": _day("2026-07-17")}


def _meta(html: str, prop: str) -> str | None:
    m = re.search(rf'<meta property="{re.escape(prop)}" content="([^"]*)"', html)
    return m.group(1) if m else None


def _pages(out: Path):
    return sorted(out.rglob("*.html"))


# --- every page, every tag ----------------------------------------------------------------------

def test_every_rendered_page_carries_the_full_og_set():
    out = _build(DAYS)
    pages = _pages(out)
    assert len(pages) >= 6, f"expected a real site, got {len(pages)} pages"
    for f in pages:
        html = f.read_text(encoding="utf-8")
        for prop in _REQUIRED:
            assert _meta(html, prop), f"{f.relative_to(out)} is missing {prop}"
        assert '<meta name="twitter:card" content="summary_large_image">' in html, f.name
        assert '<link rel="canonical"' in html, f.name


def test_og_url_matches_each_pages_actual_location():
    """THE one a typo cannot survive: 16 call sites pass `path=` by hand, and a wrong value renders a
    perfect page whose card points at a different (or nonexistent) URL."""
    out = _build(DAYS)
    for f in _pages(out):
        rel = f.relative_to(out).as_posix()
        expected = (f"{config.SITE_URL}/" if rel == "index.html" else f"{config.SITE_URL}/{rel}")
        got = _meta(f.read_text(encoding="utf-8"), "og:url")
        assert got == expected, f"{rel}: og:url is {got!r}, should be {expected!r}"


def test_canonical_and_og_url_agree():
    out = _build(DAYS)
    for f in _pages(out):
        html = f.read_text(encoding="utf-8")
        canon = re.search(r'<link rel="canonical" href="([^"]*)"', html).group(1)
        assert canon == _meta(html, "og:url"), f"{f.name}: canonical and og:url disagree"


def test_og_title_matches_the_page_title():
    out = _build(DAYS)
    for f in _pages(out):
        html = f.read_text(encoding="utf-8")
        title = re.search(r"<title>([^<]*)</title>", html).group(1)
        assert _meta(html, "og:title") == title, f"{f.name}: og:title diverges from <title>"


def test_og_description_is_never_empty_and_is_page_specific():
    out = _build(DAYS)
    descs = {}
    for f in _pages(out):
        d = _meta(f.read_text(encoding="utf-8"), "og:description")
        assert d and d.strip(), f"{f.name}: empty og:description"
        descs[f.relative_to(out).as_posix()] = d
    # the two day pages must not share one boilerplate description
    day_descs = {k: v for k, v in descs.items() if k.startswith("day/") and k != "day/index.html"}
    assert len(set(day_descs.values())) == len(day_descs), f"day pages share a description: {day_descs}"


# --- the image ----------------------------------------------------------------------------------

def test_og_image_exists_and_is_exactly_the_declared_size():
    """The declared width/height must not be able to lie: read the real PNG header."""
    assert OG_PNG.exists(), "site/public/og.png is missing — every link card would unfurl imageless"
    w, h = struct.unpack(">II", OG_PNG.read_bytes()[16:24])
    assert (w, h) == (config.OG_IMAGE_W, config.OG_IMAGE_H), (
        f"og.png is {w}x{h} but config declares {config.OG_IMAGE_W}x{config.OG_IMAGE_H}")
    assert (w, h) == (1200, 630), "1200x630 is the Open Graph size Bluesky/Slack/iMessage crop to"


def test_og_image_url_is_absolute_and_points_at_that_file():
    out = _build(DAYS)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert _meta(html, "og:image") == f"{config.SITE_URL}/{config.OG_IMAGE}"
    assert config.OG_IMAGE == OG_PNG.name


# --- gating + escaping ---------------------------------------------------------------------------

def test_og_meta_is_not_behind_a_features_flag():
    """Chrome, not a feature: a link card gated on a flag means every share before the flip unfurls
    bare, permanently, in caches nobody controls."""
    saved = dict(config.FEATURES)
    try:
        for state in (False, True):
            for k in config.FEATURES:
                config.FEATURES[k] = state
            html = site.page("t", "<p>b</p>", depth=0, path="index.html")
            for prop in _REQUIRED:
                assert _meta(html, prop), f"{prop} vanished with all flags {state}"
    finally:
        config.FEATURES.clear()
        config.FEATURES.update(saved)


def test_og_values_escape_quotes_and_angle_brackets():
    """Real composites contain literal double quotes; an unescaped one ends the attribute and the rest
    of the sentence becomes markup."""
    nasty = 'He said "we must act" <script>alert(1)</script> & soon'
    html = site.page(nasty, "<p>b</p>", depth=0, description=nasty, path="about.html")
    for prop in ("og:title", "og:description"):
        v = _meta(html, prop)
        assert v is not None and '"' not in v and "<" not in v, f"{prop} not escaped: {v!r}"
        assert "&quot;" in v and "&lt;" in v, f"{prop} lost its escaping: {v!r}"
    assert "<script>alert(1)</script>" not in html


def test_og_description_is_built_from_the_argument_not_from_composite_prose():
    """Article XIII. `page()` must derive og:description from its own `description` argument only.
    Sourcing it from day_json composites would bypass privacy_correct_line() — which can WITHHOLD or
    RECOMPOSE a composite — and republish the withheld text into a surface no audit scans."""
    # Checked against the AST, not the source text: comments and the docstring DISCUSS composites (the
    # rule has to be written down where it is enforced), and a substring grep would fire on the very
    # explanation of the rule. What matters is whether page() actually reads that data.
    import ast
    import inspect
    import textwrap

    fn = ast.parse(textwrap.dedent(inspect.getsource(site.page))).body[0]
    body = fn.body[1:] if (isinstance(fn.body[0], ast.Expr)
                           and isinstance(fn.body[0].value, ast.Constant)) else fn.body
    referenced = {n.value for stmt in body for n in ast.walk(stmt)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    referenced |= {n.attr for stmt in body for n in ast.walk(stmt) if isinstance(n, ast.Attribute)}
    referenced |= {n.id for stmt in body for n in ast.walk(stmt) if isinstance(n, ast.Name)}
    leaked = {"daily_lines", "composite", "talking_points", "day_json"} & referenced
    assert not leaked, (
        f"page() now reads {sorted(leaked)} — og: values must come from its arguments only, or they "
        f"bypass privacy_correct_line() and republish withheld text into an unaudited surface")
    html = site.page("T", "<p>the body text</p>", depth=0, description="D", path="about.html")
    assert _meta(html, "og:description") == "D"
    assert "the body text" not in (_meta(html, "og:description") or "")
