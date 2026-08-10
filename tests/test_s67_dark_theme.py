"""S67-5: the dark variant of the one stylesheet.

The design register is unchanged: system fonts, the same density, the same two party hues. Only
the surfaces invert. What is pinned here is that the variant actually ships on every page, that
nothing in the stylesheet was left behind as a literal (a literal is a rule with only one theme),
and that both palettes clear the same contrast bar. Article IV lives in the last one: if a party
hue is legible on dark and the other is not, the instrument has a favourite.
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from pipeline import config, site


DAY = "2026-02-17"
SLUG = "dark-phrase"
DARK_QUERY = "@media (prefers-color-scheme: dark)"


def _build() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="onscript-s67-dark-"))
    derived, out = tmp / "derived", tmp / "public"
    (derived / "days").mkdir(parents=True)
    (derived / "phrases").mkdir(parents=True)
    (derived / "days" / f"{DAY}.json").write_text(json.dumps({
        "day": DAY,
        "daily_lines": {p: {"composite": f"{p} line.", "generator": "deterministic"}
                        for p in ("D", "R")},
        "top_synchronized": [{"ngram": "dark theme phrase", "slug": SLUG, "party": "D",
                              "day_peak": 4, "counts": {"D": 4, "R": 1}, "series": [1, 2, 4],
                              "first_seen": {"date": "2026-02-15"}}],
    }), encoding="utf-8")
    (derived / "phrases" / f"{SLUG}.json").write_text(json.dumps({
        "slug": SLUG, "ngram": "dark theme phrase", "first_seen": {"date": "2026-02-15"},
        "series": [{"day": "2026-02-15", "D": 1, "R": 0}, {"day": "2026-02-16", "D": 2, "R": 1},
                   {"day": DAY, "D": 4, "R": 1}]}), encoding="utf-8")
    saved = (site.DERIVED, site.OUT, config.DERIVED)
    try:
        site.DERIVED, site.OUT, config.DERIVED = derived, out, derived
        site.build_site()
    finally:
        site.DERIVED, site.OUT, config.DERIVED = saved
    return out


def _palettes() -> tuple[dict, dict]:
    blocks = re.findall(r":root\s*\{(.*?)\}", site.CSS, re.S)
    assert len(blocks) == 2, "expected exactly one light and one dark :root palette"
    return (dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{3,6})", blocks[0])),
            dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{3,6})", blocks[1])))


def _luminance(color: str) -> float:
    if len(color) == 4:
        color = "#" + "".join(c * 2 for c in color[1:])
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    channels = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
    return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2]


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + .05) / (lo + .05)


def test_the_dark_variant_ships_on_every_rendered_page():
    out = _build()
    pages = sorted(out.rglob("*.html"))
    assert len(pages) >= 8
    for page in pages:
        assert DARK_QUERY in page.read_text(encoding="utf-8"), page


def test_the_dark_block_redefines_every_token_the_light_block_declares():
    """A token the dark block forgets keeps its light value, which is how a near-white panel
    survives into a dark page."""
    light, dark = _palettes()
    missing = sorted(set(light) - set(dark))
    assert missing == [], f"the dark palette does not define {missing}"


def test_body_text_clears_aa_on_both_themes():
    light, dark = _palettes()
    for name, palette in (("light", light), ("dark", dark)):
        assert _contrast(palette["ink"], palette["bg"]) >= 7.0, name
        assert _contrast(palette["ink"], palette["panel"]) >= 7.0, name
        assert _contrast(palette["muted"], palette["panel"]) >= 4.5, name
        assert _contrast(palette["faint"], palette["bg"]) >= 4.5, name
        assert _contrast(palette["faint"], palette["panel"]) >= 4.5, name


def test_both_party_hues_are_legible_on_their_own_theme_and_neither_is_favoured():
    """Article IV. A party colour that reads on dark while the other smudges is a claim about
    which party is easier to read."""
    light, dark = _palettes()
    for name, palette in (("light", light), ("dark", dark)):
        blue = _contrast(palette["blue"], palette["panel"])
        red = _contrast(palette["red"], palette["panel"])
        assert blue >= 4.5 and red >= 4.5, f"{name}: blue {blue:.2f}, red {red:.2f}"
        assert abs(blue - red) <= 2.0, (
            f"{name}: the two party hues differ by {abs(blue - red):.2f} in contrast")


def test_the_warning_and_status_colours_stay_readable_on_both_themes():
    light, dark = _palettes()
    for name, palette in (("light", light), ("dark", dark)):
        assert _contrast(palette["warn-ink"], palette["warn-bg"]) >= 4.5, name
        assert _contrast(palette["ok"], palette["panel"]) >= 3.0, name
        assert _contrast(palette["code-ink"], palette["code-bg"]) >= 7.0, name


def test_the_keyspan_highlight_keeps_the_quote_readable_on_both_themes():
    """The mark sits behind body text; if the highlight is bright on a dark theme the quote
    disappears into it."""
    light, dark = _palettes()
    for name, palette in (("light", light), ("dark", dark)):
        assert _contrast(palette["ink"], palette["mark-bg"]) >= 4.5, name


def test_no_stylesheet_rule_was_left_as_a_single_theme_literal():
    """Every colour outside the two :root blocks must come from a token, or it only has one
    theme. The legend swatch's inline var() is the pattern to follow, not an exception."""
    without_palettes = re.sub(r":root\s*\{.*?\}", "", site.CSS, flags=re.S)
    literals = re.findall(r":\s*(#[0-9a-fA-F]{3,6})", without_palettes)
    assert literals == [], f"stylesheet rules still hard-code {sorted(set(literals))}"


def test_the_charts_inherit_the_theme_rather_than_carrying_their_own_colours():
    out = _build()
    for page in out.rglob("*.html"):
        for svg in re.findall(r"<svg\b.*?</svg>", page.read_text(encoding="utf-8"), re.S):
            literals = re.findall(r'(?:stroke|fill)="(#[0-9a-fA-F]{3,6})"', svg)
            assert literals == [], f"{page.name}: an SVG hard-codes {literals}"
