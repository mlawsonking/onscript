"""S67-3: per-page Open Graph cards, and the fence around the project's first third-party package.

Two things are being protected here and they pull in opposite directions. The cards have to carry
real numbers, which means real code runs on every assemble. And Pillow is decorative, which means
none of that code may ever be able to cost the day's artifact. So the tests come in two halves:
the pixels are deterministic and correct, and the absence of the whole subsystem is a normal,
silent, correct outcome.
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import struct
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from pipeline import cards, config, run_assemble, site


ROOT = Path(__file__).resolve().parent.parent
DAY = "2026-04-07"
SLUG = "card-phrase"


def _day_json(day: str) -> dict:
    return {"day": day,
            "daily_lines": {p: {"composite": f"{p} line.", "generator": "deterministic"}
                            for p in ("D", "R")},
            "top_synchronized": [],
            "participation": {p: {"measures": {"office_participation": {
                "label": "Office participation", "numerator": 31 if p == "D" else 12,
                "numerator_unit": "offices", "denominator": 213 if p == "D" else 220,
                "denominator_unit": "eligible caucus offices", "window": day,
                "method_version": "participation-v1"}}} for p in ("D", "R")}}


PHRASE = {"slug": SLUG, "ngram": "1 8 billion",
          "first_seen": {"date": "2026-04-01"},
          "series": [{"day": "2026-04-05", "D": 4, "R": 1},
                     {"day": "2026-04-06", "D": 18, "R": 3},
                     {"day": DAY, "D": 26, "R": 5}]}


def _build(target: Path):
    return cards.build_cards([(DAY, _day_json(DAY))], [(SLUG, PHRASE)], target)


# --- the pixels -----------------------------------------------------------------------------

def test_cards_are_exactly_the_declared_open_graph_size():
    out = Path(tempfile.mkdtemp(prefix="onscript-s67-card-"))
    _build(out)
    for relative in (f"{config.OG_CARD_DIR}/day/{DAY}.png", f"{config.OG_CARD_DIR}/phrases/{SLUG}.png"):
        raw = (out / relative).read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", relative
        assert struct.unpack(">II", raw[16:24]) == (config.OG_IMAGE_W, config.OG_IMAGE_H), relative


def test_two_renders_of_one_input_are_byte_identical():
    """The determinism claim, proven rather than asserted: a card that moved every run would
    churn the data commit forever and make the diff useless."""
    digests = []
    for _ in range(2):
        out = Path(tempfile.mkdtemp(prefix="onscript-s67-det-"))
        _build(out)
        digests.append(hashlib.sha256(
            (out / config.OG_CARD_DIR / "phrases" / f"{SLUG}.png").read_bytes()).hexdigest())
    assert digests[0] == digests[1]


def test_an_unchanged_card_is_not_rewritten():
    out = Path(tempfile.mkdtemp(prefix="onscript-s67-idem-"))
    first = _build(out)
    second = _build(out)
    assert first["written"] == 2 and first["unchanged"] == 0
    assert second["written"] == 0 and second["unchanged"] == 2


def test_no_clock_reaches_a_pixel():
    """`generated_at` is a parameter and it appears only in the manifest. Two cards built at
    different notional times must be the same bytes."""
    a, b = (Path(tempfile.mkdtemp(prefix=f"onscript-s67-clk{i}-")) for i in "ab")
    cards.build_cards([(DAY, _day_json(DAY))], [], a, generated_at="2020-01-01T00:00:00Z")
    cards.build_cards([(DAY, _day_json(DAY))], [], b, generated_at="2099-12-31T23:59:59Z")
    name = f"{config.OG_CARD_DIR}/day/{DAY}.png"
    assert (a / name).read_bytes() == (b / name).read_bytes()
    assert json.loads((a / config.OG_CARD_DIR / "index.json").read_text(encoding="utf-8")) \
        != json.loads((b / config.OG_CARD_DIR / "index.json").read_text(encoding="utf-8"))


def test_the_renderer_uses_the_raster_font_and_never_a_freetype_face():
    """load_default() returns a FreeType-rendered Aileron wherever Pillow was built with FreeType,
    and FreeType hinting is not guaranteed identical between platform wheels. The bitmap accessor
    is the only one that keeps CI and a laptop in agreement."""
    # Checked on the AST, not the text: the module docstring DISCUSSES load_default() because the
    # rule has to be written down where it is enforced, and a substring grep would fire on the
    # explanation of the rule itself.
    import inspect
    import textwrap
    fn = ast.parse(textwrap.dedent(inspect.getsource(cards._font))).body[0]
    names = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    names |= {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
    assert "load_default_imagefont" in names
    assert "load_default" not in names and "truetype" not in names
    assert type(cards._font()).__name__ == "ImageFont", (
        "the raster font must not be a FreeTypeFont")


def test_non_ascii_source_text_folds_instead_of_raising():
    """The raster font cannot encode above U+00FF, and office names really do carry curly
    apostrophes and accents. The fold is explicit so the pixels stay specified."""
    assert cards._ascii("O’Halleran — café “quote”") == "O'Halleran - cafe \"quote\""
    assert cards._ascii("中文") == "??"


# --- the content ----------------------------------------------------------------------------

def test_the_card_carries_the_headline_counts_with_their_denominators():
    out = Path(tempfile.mkdtemp(prefix="onscript-s67-content-"))
    _build(out)
    manifest = json.loads((out / config.OG_CARD_DIR / "index.json").read_text(encoding="utf-8"))
    alt = manifest["cards"][f"day/{DAY}"]["alt"]
    assert "31 of 213 offices" in alt and "12 of 220 offices" in alt


def test_the_card_names_both_parties_and_gives_each_a_non_color_cue():
    """A PNG cannot be restyled, zoomed or hovered, so the party distinction may not rest on hue."""
    rows = [("D", "31 of 213 offices", "base"), ("R", "12 of 220 offices", "base")]
    assert cards.PARTY_DASHED["D"] is False and cards.PARTY_DASHED["R"] is True
    alt = cards._alt("day", DAY, rows)
    assert "Democrats" in alt and "Republicans" in alt


def test_alt_text_is_authored_where_the_card_is_authored():
    """One owner for the image and its description; the renderer must not re-derive an alt string
    from a filename, or the two drift the first time the card design changes."""
    source = (ROOT / "pipeline" / "site.py").read_text(encoding="utf-8")
    fn = ast.parse(re.search(r"def _card_for\(.*?\n\n\n", source, re.S).group(0)).body[0]
    literals = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "alt" in literals and not any("OnScript share card" in s for s in literals)


def test_a_suppressed_phrase_gets_no_card():
    from pipeline import privacy
    original = privacy.is_suppressed
    try:
        privacy.is_suppressed = lambda text: "billion" in str(text)
        out = Path(tempfile.mkdtemp(prefix="onscript-s67-priv-"))
        stats = cards.build_cards([], [(SLUG, PHRASE)], out)
        assert stats["cards"] == 0
        assert not (out / config.OG_CARD_DIR / "phrases").exists()
    finally:
        privacy.is_suppressed = original


# --- the fence ------------------------------------------------------------------------------

def test_pillow_is_imported_in_exactly_one_module():
    offenders = []
    for path in sorted((ROOT / "pipeline").rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py")):
        if path.name == "cards.py":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"^\s*(?:from PIL\b|import PIL\b)", text, re.MULTILINE):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == [], f"PIL leaked outside pipeline/cards.py: {offenders}"


def test_the_card_builder_is_the_last_optional_step_of_run_assemble():
    """AFTER the day summary and the manifest, and wrapped. The placement IS the safety story."""
    source = (ROOT / "pipeline" / "run_assemble.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_share_cards")
    assert any(isinstance(n, ast.Try) for n in ast.walk(fn)), "_share_cards must be wrapped"
    handlers = [h for n in ast.walk(fn) if isinstance(n, ast.Try) for h in n.handlers]
    assert any(isinstance(h.type, ast.Name) and h.type.id == "Exception" for h in handlers)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = [n.func.id for n in ast.walk(main)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert "_share_cards" in calls
    # assemble() writes the day JSON and the manifest; nothing in it may call the card builder.
    assemble = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "assemble")
    assert "_share_cards" not in [n.func.id for n in ast.walk(assemble)
                                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]


def test_a_broken_card_builder_is_logged_and_costs_nothing_else():
    """Day-one state, enumerated: no Pillow installed and no cards directory. That is what every
    live deployment looks like right now, and it must be a silent, correct outcome."""
    log = io.StringIO()
    original = cards.build_cards
    try:
        def boom(*_a, **_k):
            raise ImportError("No module named 'PIL'")
        cards.build_cards = boom
        with redirect_stdout(log):
            run_assemble._share_cards()
    finally:
        cards.build_cards = original
    assert "[cards] skipped (skip-and-log):" in log.getvalue()
    assert "brand link card" in log.getvalue()


def test_a_page_without_a_card_keeps_the_brand_card():
    html = site.page("T", "<p>b</p>", depth=0, path="index.html")
    assert f'<meta property="og:image" content="{config.SITE_URL}/{config.OG_IMAGE}">' in html


def test_a_page_with_a_card_points_at_it_with_an_absolute_url():
    html = site.page("T", "<p>b</p>", depth=1, path=f"day/{DAY}.html",
                     card=f"{config.OG_CARD_DIR}/day/{DAY}.png", card_alt="probe alt")
    assert f'content="{config.SITE_URL}/{config.OG_CARD_DIR}/day/{DAY}.png"' in html
    assert 'content="probe alt"' in html


def test_a_manifest_naming_a_missing_file_falls_back_rather_than_linking_a_404():
    saved_index, saved_out = site._CARD_INDEX, site.OUT
    try:
        site.OUT = Path(tempfile.mkdtemp(prefix="onscript-s67-miss-"))
        site._CARD_INDEX = {"day/x": {"path": "cards/day/x.png", "alt": "a"}}
        assert site._card_for("day/x") == {}
    finally:
        site._CARD_INDEX, site.OUT = saved_index, saved_out


def test_the_pinned_version_agrees_across_the_lock_the_sbom_and_the_workflow():
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    version = re.search(r"pillow==([0-9.]+)", lock).group(1)
    sbom = json.loads((ROOT / "sbom.spdx.json").read_text(encoding="utf-8"))
    entry = next(row for row in sbom["packages"] if row["name"] == "Pillow")
    assert entry["versionInfo"] == version
    assert "OPTIONAL" in entry["comment"] and "cards.py" in entry["comment"]
    assert lock.count("--hash=sha256:") >= 2, "a pin without artifact hashes is a name, not a pin"
    workflow = (ROOT / ".github" / "workflows" / "assemble.yml").read_text(encoding="utf-8")
    assert "--require-hashes -r requirements.lock" in workflow
    install = next(line for line in workflow.splitlines() if "pip install" in line)
    following = workflow.split(install, 1)[1].splitlines()[0:2]
    assert any("||" in line for line in [install] + following), (
        "the optional install must not be able to fail the run")
