"""Per-page Open Graph share cards (S67-3): 1200x630 PNGs with the page's own numbers.

WHY THIS EXISTS. Every share of this site unfurls through one image. Until now that image was the
generic brand card on all 660-odd pages, so a link to "the day 53 Democratic offices said the same
sentence" looked exactly like a link to the About page. The numbers are the product; the card is the
only part of the product most people will ever see.

WHY IT CANNOT BREAK THE DAY (docs/37 rule 4, and the standing skip-and-log rule). Pillow is the
FIRST third-party runtime dependency this project has ever taken, and it is taken for decoration.
So the blast radius is fenced three ways:

  * ``PIL`` is imported HERE and nowhere else, inside the builder function, so an absent or broken
    Pillow is an ImportError raised at the one call site that already catches everything.
  * The one caller is the optional skip-and-log block in run_assemble, which runs AFTER the day
    summary and the manifest are on disk. Nothing downstream of it depends on a card existing.
  * site.py points ``og:image`` at a card only when the manifest names it AND the file is present,
    and falls back to the brand card otherwise. DAY ONE STATE, enumerated: no Pillow installed and
    no cards directory is the state every existing deployment is in right now, and it renders
    exactly the site that shipped yesterday.

DETERMINISM. The bytes are a pure function of the arguments.

  * No clock. ``generated_at`` is a parameter and appears only in the manifest, never in a pixel;
    a card that embedded a render time would differ on every run and churn the commit forever.
  * No system fonts and no FreeType. ``ImageFont.load_default()`` returns a FreeType-rendered
    Aileron on any Pillow that was built with FreeType, and FreeType hinting is not guaranteed
    identical between the Windows wheel and the manylinux one. So this module uses
    ``load_default_imagefont()``, Pillow's embedded 6x11 raster font, and scales it with
    integer NEAREST resampling. The look is deliberately blunt and instrument-like, and the
    pixels are reproducible by construction rather than by hope. If a designed typeface is wanted
    later, the answer is a vendored TTF committed to the repository, not a system font lookup.
  * Text wraps on a character count, because a fixed-width raster font makes glyph width a
    constant rather than a measurement.

The card text is measurement output: dates, counts, denominators, and the normalized n-gram itself.
No composite prose and no source statement text, the same rule the Atom entries and the og: values
follow, for the same reason: this surface is scanned by no publication audit.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config, privacy, util

# The Open Graph frame every consumer crops to. Read from config so the declared og:image:width and
# the actual pixels cannot disagree (tests/test_og_meta.py already reads the real PNG header).
CARD_W, CARD_H = config.OG_IMAGE_W, config.OG_IMAGE_H

# The light design, fixed. A PNG cannot answer a media query, so a card that tried to serve both
# themes would serve neither; these match the light stylesheet's tokens.
INK = (26, 26, 26)
MUTED = (90, 90, 90)
FAINT = (112, 112, 112)
LINE = (226, 226, 226)
BG = (251, 251, 249)
PANEL = (255, 255, 255)
PARTY_RGB = {"D": (43, 76, 126), "R": (138, 47, 47)}
PARTY_NAME = {"D": "Democrats", "R": "Republicans"}
# The non-color cue, matching the site's charts: D solid, R dashed. A card is the one surface a
# reader cannot hover, zoom or restyle, so the party distinction may not rest on hue alone.
PARTY_DASHED = {"D": False, "R": True}

MARGIN = 56
GLYPH_W, GLYPH_H = 6, 11        # the embedded raster font's fixed cell


def _font():
    """Pillow's embedded raster font, explicitly.

    ``load_default_imagefont`` (Pillow 11+) is the only accessor that guarantees the legacy bitmap
    and never a FreeType face. Its absence is a real incompatibility and is raised, not worked
    around: a silent fallback to ``load_default()`` would swap the font underneath a determinism
    claim, and the caller's skip-and-log turns the raise into a logged skip."""
    from PIL import ImageFont
    loader = getattr(ImageFont, "load_default_imagefont", None)
    if loader is None:
        raise RuntimeError(
            "Pillow is too old for deterministic cards: ImageFont.load_default_imagefont() "
            "(Pillow 11+) is required, because load_default() returns a FreeType face whose "
            "hinting is not identical across platform wheels")
    return loader()


# The embedded raster font carries one glyph per byte and cannot encode anything above U+00FF, so
# a curly apostrophe in a member's office name used to raise UnicodeEncodeError mid-render. Folding
# to ASCII is done HERE, explicitly and deterministically, rather than by catching the error: the
# whole value of this module is that the same input produces the same pixels, and "whatever the
# codec did" is not a specification.
# Written as codepoint escapes rather than as the characters themselves, for the same reason
# the house em-dash detector is (S66-4): a table of confusable punctuation is unreadable when
# every entry looks like every other entry, and docs/25 bans the em dash from this corpus even
# where it is data rather than prose.
_FOLD = {
    "\u2018": "'", "\u2019": "'", "\u201a": ",", "\u201b": "'",      # single quotes
    "\u201c": '"', "\u201d": '"', "\u201e": '"',                     # double quotes
    "\u2032": "'", "\u2033": '"',                                    # prime, double prime
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",      # hyphen through en dash
    "\u2014": "-", "\u2015": "-",                                    # em dash, horizontal bar
    "\u2026": "...", "\u2022": "*", "\u00b7": "-", "\u2044": "/",    # ellipsis, bullet, solidus
    "\u00a0": " ", "\u2009": " ", "\u202f": " ", "\u200b": "",      # spaces and the zero width
}


def _ascii(text: str) -> str:
    """Deterministic ASCII folding: named punctuation first, then accent stripping, then '?'."""
    import unicodedata
    folded = "".join(_FOLD.get(ch, ch) for ch in str(text or ""))
    decomposed = unicodedata.normalize("NFKD", folded)
    out = []
    for ch in decomposed:
        if unicodedata.combining(ch):
            continue
        out.append(ch if 32 <= ord(ch) <= 126 else ("?" if ch.strip() else " "))
    return "".join(out)


def _wrap(text: str, cols: int) -> list[str]:
    """Greedy word wrap at a character count. Fixed-width font, so columns are exact."""
    words, lines, current = _ascii(text).split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= cols or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _text(image, text: str, x: int, y: int, scale: int, fill, *, bold: bool = False) -> int:
    """Draw one line at ``scale`` times the raster cell and return the y below it.

    The line is rendered once at 1x into its own mask and then NEAREST-upscaled, so the result is
    an exact integer magnification of the embedded raster: no hinting, no subpixel positioning, no
    platform in the loop.

    ``bold`` composites the upscaled mask a second time two DEVICE pixels right. Doing it before the
    upscale (the obvious way) widens the stroke by a whole magnified cell, which at scale 6 is a
    36-pixel smear rather than a weight."""
    from PIL import Image, ImageDraw
    line = _ascii(text)
    if not line:
        return y + GLYPH_H * scale
    w = max(1, len(line) * GLYPH_W)
    mask = Image.new("L", (w, GLYPH_H), 0)
    ImageDraw.Draw(mask).text((0, 0), line, font=_FONT, fill=255)
    big = mask.resize((w * scale, GLYPH_H * scale), Image.NEAREST)
    image.paste(fill, (x, y), big)
    if bold:
        image.paste(fill, (x + max(1, scale // 2), y), big)
    return y + GLYPH_H * scale


def _rule(draw, y: int, color=LINE, height: int = 2) -> None:
    draw.rectangle([MARGIN, y, CARD_W - MARGIN, y + height - 1], fill=color)


def _party_bar(draw, x: int, y: int, height: int, party: str) -> None:
    """The party's vertical rule: solid for D, segmented for R (the non-color cue)."""
    width = 10
    if not PARTY_DASHED.get(party):
        draw.rectangle([x, y, x + width - 1, y + height - 1], fill=PARTY_RGB[party])
        return
    step, on = 22, 12
    for top in range(y, y + height, step):
        bottom = min(top + on - 1, y + height - 1)
        draw.rectangle([x, top, x + width - 1, bottom], fill=PARTY_RGB[party])


def _canvas():
    from PIL import Image, ImageDraw
    image = Image.new("RGB", (CARD_W, CARD_H), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle([MARGIN - 24, MARGIN - 20, CARD_W - MARGIN + 24, CARD_H - MARGIN + 20], fill=PANEL)
    return image, draw


def _header(image, draw, kicker: str) -> int:
    """Wordmark, kicker, rule. Every y is derived from the one before it, so a scale change moves
    the layout with it instead of colliding with a hard-coded rule position."""
    y = _text(image, "OnScript", MARGIN, MARGIN, 4, INK, bold=True)
    y = _text(image, kicker, MARGIN, y + 8, 2, FAINT)
    _rule(draw, y + 14)
    return y + 44


def _footer(image, draw) -> None:
    _rule(draw, CARD_H - MARGIN - 34)
    _text(image, "onscript.news   Automated measurement of congressional language",
          MARGIN, CARD_H - MARGIN - 20, 2, MUTED)


def _party_rows(image, draw, y: int, rows: list[tuple[str, str, str]]) -> int:
    """One block per party: bar, name, headline count, denominator note."""
    for party, headline, note in rows:
        block_h = 74
        _party_bar(draw, MARGIN, y, block_h, party)
        left = MARGIN + 26
        _text(image, PARTY_NAME.get(party, party), left, y, 2, PARTY_RGB.get(party, INK), bold=True)
        _text(image, headline, left, y + 24, 3, INK)
        _text(image, note, left, y + 54, 2, FAINT)
        y += block_h + 16
    return y


def day_card(day: str, rows: list[tuple[str, str, str]], subtitle: str = ""):
    """The card for one published day: the date, then each party's participation with its base."""
    image, draw = _canvas()
    y = _header(image, draw, "Congressional language, measured daily")
    y = _text(image, str(day), MARGIN, y, 6, INK, bold=True)
    if subtitle:
        y = _text(image, subtitle, MARGIN, y + 10, 2, MUTED) + 14
    else:
        y += 20
    _party_rows(image, draw, y, rows)
    _footer(image, draw)
    return image


def phrase_card(ngram: str, rows: list[tuple[str, str, str]], subtitle: str = ""):
    """The card for one tracked phrase: the normalized key, then each party's peak with its base."""
    image, draw = _canvas()
    y = _header(image, draw, "Tracked phrase")
    for line in _wrap(str(ngram), 30)[:3]:
        y = _text(image, line, MARGIN, y, 5, INK, bold=True)
    if subtitle:
        y = _text(image, subtitle, MARGIN, y + 10, 2, MUTED) + 14
    else:
        y += 20
    _party_rows(image, draw, y, rows)
    _footer(image, draw)
    return image


def _alt(kind: str, subject: str, rows: list[tuple[str, str, str]]) -> str:
    """The card's alt text, authored where the card is authored (one owner for both, docs/37 r6)."""
    body = "; ".join(f"{PARTY_NAME.get(p, p)} {headline}" for p, headline, _ in rows)
    lead = (f"OnScript share card for {subject}" if kind == "day"
            else f"OnScript share card for the tracked phrase {subject}")
    return f"{lead}. {body}." if body else f"{lead}."


def _write_png(image, path: Path) -> bool:
    """Write only when the bytes actually change, so an unchanged card is not a commit.

    ``optimize`` is deliberately off: it is a deflate strategy search, and a search is exactly the
    kind of thing that can differ between zlib builds."""
    import io
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=6)
    payload = buffer.getvalue()
    if path.exists() and path.read_bytes() == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return True


_FONT = None


def build_cards(days: list[tuple[str, dict]], phrases: list[tuple[str, dict]], out_dir: Path,
                *, symmetry_dir: Path | None = None, generated_at: str | None = None) -> dict:
    """Render every day and phrase card under ``out_dir``/cards and write their manifest.

    ``days`` is [(day, day_json)] and ``phrases`` is [(slug, phrase_json)], both supplied by the
    caller so this module never decides what is published. Returns build statistics."""
    global _FONT
    _FONT = _font()          # raises before any file is touched if the font contract is unmet
    from .phrase_window import public_phrase_window

    out_dir = Path(out_dir)
    cards_dir = out_dir / config.OG_CARD_DIR
    symmetry_dir = Path(symmetry_dir) if symmetry_dir else None
    manifest: dict[str, dict] = {}
    written = unchanged = 0

    def caucus(day: str) -> dict:
        if not symmetry_dir:
            return {}
        report = util.read_json(symmetry_dir / f"{day}.json", {}) or {}
        parties = report.get("parties") or {}
        return {p: (parties.get(p) or {}).get("date_effective_eligible_caucus_offices")
                for p in config.COMPOSITE_PARTIES}

    for day, data in days:
        participation = (data or {}).get("participation") or {}
        rows = []
        for party in config.COMPOSITE_PARTIES:
            measure = ((participation.get(party) or {}).get("measures") or {}).get("office_participation") or {}
            numerator, denominator = measure.get("numerator"), measure.get("denominator")
            if numerator is None or denominator is None:
                continue
            rows.append((party, f"{numerator} of {denominator} offices",
                         str(measure.get("label") or "offices publishing an eligible claim")))
        if not rows:
            continue
        key = f"day/{day}"
        image = day_card(day, rows, subtitle="Offices publishing an eligible message claim")
        if _write_png(image, cards_dir / "day" / f"{day}.png"):
            written += 1
        else:
            unchanged += 1
        manifest[key] = {"path": f"{config.OG_CARD_DIR}/day/{day}.png",
                         "alt": _alt("day", day, rows)}

    for slug, data in phrases:
        ngram = (data or {}).get("ngram") or ""
        # Art. XIII at the card gate too: a card is a public file with its own URL, and it is
        # unfurled by crawlers that never read the page it belongs to.
        if not ngram or privacy.is_suppressed(ngram):
            continue
        window = public_phrase_window(data)
        peak_day = window.get("peak_day") or ""
        series = window.get("series") or []
        if not peak_day or not series:
            continue
        denominators = caucus(peak_day)
        rows = []
        for party in config.COMPOSITE_PARTIES:
            peak = 0
            for row in series:
                try:
                    peak = max(peak, int(row.get(party) or 0))
                except (TypeError, ValueError):
                    continue
            denominator = denominators.get(party)
            headline = (f"peak {peak} of {denominator} offices" if denominator
                        else f"peak {peak} offices")
            base = (f"largest single day, window from {window.get('first_day') or peak_day}"
                    if denominator is None else
                    f"of eligible caucus offices, window from {window.get('first_day') or peak_day}")
            rows.append((party, headline, base))
        image = phrase_card(ngram, rows, subtitle=f"Peak day {peak_day}")
        if _write_png(image, cards_dir / "phrases" / f"{slug}.png"):
            written += 1
        else:
            unchanged += 1
        manifest[f"phrases/{slug}"] = {"path": f"{config.OG_CARD_DIR}/phrases/{slug}.png",
                                       "alt": _alt("phrase", ngram, rows)}

    cards_dir.mkdir(parents=True, exist_ok=True)
    payload = {"cards": dict(sorted(manifest.items()))}
    if generated_at:
        payload["generated_at"] = generated_at
    (cards_dir / "index.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8")
    stats = {"cards": len(manifest), "written": written, "unchanged": unchanged}
    print(f"[cards] {stats}")
    return stats
