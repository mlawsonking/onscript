"""S74-8 Package A (R-74.3): publication by date gate.

An essay whose date is after the product day is not loaded, so it leaves zero bytes anywhere in the
build: no page, no index row, no sitemap or feed entry, no nav link, no copied figure. The same
essay appears in the first render whose product day reaches its date. The live self-audit essay is
unaffected. One test is built from the real committed content/essays tree (docs/37 §2).
"""
from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path

from pipeline import public_strings, site

from tests.test_s67_essays_and_clarity import STUB_SVG, _build, _essay

FUTURE = "2026-12-24"
MARKER = "gate-probe-unique-marker"


def _gated_essay(date: str = FUTURE) -> dict:
    essay = _essay(slug="gate-probe", date=date)
    essay["title"] = f"Title {MARKER}"
    essay["dek"] = f"Dek {MARKER}"
    essay["figures"] = [{"src": "figures/gate-probe-fig.svg", "after_block": 1,
                         "alt": "probe", "caption": "probe"}]
    return essay


def _build_on(directory: Path, product_day: str) -> Path:
    saved = site.essay_gate_day
    try:
        site.essay_gate_day = lambda: product_day
        return _build(essays_dir=directory)
    finally:
        site.essay_gate_day = saved


def _tree_with_real_essays_plus_probe(date: str = FUTURE) -> Path:
    """A copy of the real committed content/essays tree with one future-dated probe added."""
    directory = Path(tempfile.mkdtemp(prefix="onscript-s74-8-gate-"))
    shutil.copytree(site.ESSAYS_DIR, directory, dirs_exist_ok=True)
    (directory / "gate-probe.json").write_text(json.dumps(_gated_essay(date)), encoding="utf-8")
    (directory / "figures" / "gate-probe-fig.svg").write_bytes(STUB_SVG)
    return directory


def _all_bytes(out: Path) -> list[tuple[Path, bytes]]:
    return [(p, p.read_bytes()) for p in out.rglob("*") if p.is_file()]


def test_the_gate_compares_iso_days_and_refuses_what_it_cannot_read():
    assert site.essay_is_due({"date": "2026-11-20"}, "2026-11-20")
    assert site.essay_is_due({"date": "2026-08-19"}, "2026-11-20")
    assert not site.essay_is_due({"date": "2026-11-21"}, "2026-11-20")
    for bad in ("", None, "Nov 23", "2026-11-2", "2026-11-23T00:00"):
        assert not site.essay_is_due({"date": bad}, "2026-12-31"), bad


def test_load_essays_drops_future_dates_and_keeps_today_and_earlier():
    directory = Path(tempfile.mkdtemp(prefix="onscript-s74-8-load-"))
    for slug, date in (("past", "2026-11-01"), ("today", "2026-11-20"), ("future", "2026-11-21")):
        (directory / f"{slug}.json").write_text(json.dumps(_essay(slug, date)), encoding="utf-8")
    assert [e["slug"] for e in site.load_essays(directory, product_day="2026-11-20")] == \
        ["today", "past"]
    assert [e["slug"] for e in site.load_essays(directory, product_day="2026-11-21")] == \
        ["future", "today", "past"]


def test_the_default_gate_day_is_the_product_day():
    assert site.essay_gate_day() == site.util.product_day()


def test_a_future_essay_leaves_zero_bytes_in_a_build_of_the_real_tree():
    """The production-shaped one: the real committed essays and figures, plus one future-dated
    essay. Nothing of the probe may reach the output, and the live essay renders as it does."""
    directory = _tree_with_real_essays_plus_probe()
    out = _build_on(directory, "2026-11-20")
    for path, payload in _all_bytes(out):
        assert MARKER.encode() not in payload, path
        assert b"gate-probe" not in payload, path
    assert not (out / "essays" / "gate-probe.html").exists()
    assert not (out / "essays" / "figures" / "gate-probe-fig.svg").exists()
    # The live essay is unaffected: its page, its index row, its sitemap entry, its nav link.
    assert (out / "essays" / "self-audit.html").exists()
    assert 'href="self-audit.html"' in (out / "essays" / "index.html").read_text(encoding="utf-8")
    assert "essays/self-audit.html" in (out / "sitemap.xml").read_text(encoding="utf-8")
    assert 'essays/index.html">Essays</a>' in (out / "index.html").read_text(encoding="utf-8")


def test_the_same_essay_appears_when_the_product_day_reaches_its_date():
    directory = _tree_with_real_essays_plus_probe()
    out = _build_on(directory, FUTURE)
    page = out / "essays" / "gate-probe.html"
    assert page.exists()
    assert MARKER in page.read_text(encoding="utf-8")
    assert 'href="gate-probe.html"' in (out / "essays" / "index.html").read_text(encoding="utf-8")
    assert "essays/gate-probe.html" in (out / "sitemap.xml").read_text(encoding="utf-8")
    assert (out / "essays" / "figures" / "gate-probe-fig.svg").read_bytes() == STUB_SVG
    # Newest first: the probe now leads the index, the live essay still follows.
    index = (out / "essays" / "index.html").read_text(encoding="utf-8")
    assert index.index('href="gate-probe.html"') < index.index('href="self-audit.html"')


def test_a_tree_of_only_future_essays_is_the_empty_surface():
    """Zero due essays is zero bytes and no nav link, exactly as zero essays (S67-7a)."""
    directory = Path(tempfile.mkdtemp(prefix="onscript-s74-8-onlyfuture-"))
    (directory / "gate-probe.json").write_text(json.dumps(_gated_essay()), encoding="utf-8")
    out = _build_on(directory, "2026-11-20")
    assert not (out / "essays").exists()
    for page in out.rglob("*.html"):
        assert "essays/index.html" not in page.read_text(encoding="utf-8"), page
    assert "essays" not in (out / "sitemap.xml").read_text(encoding="utf-8")


def test_a_gated_essay_with_a_malformed_figure_still_fails_the_load():
    """The gate does not hide authoring errors until the morning an essay comes due."""
    directory = Path(tempfile.mkdtemp(prefix="onscript-s74-8-badfig-"))
    essay = _gated_essay()
    essay["figures"][0]["src"] = "../x.svg"
    (directory / "gate-probe.json").write_text(json.dumps(essay), encoding="utf-8")
    try:
        site.load_essays(directory, product_day="2026-11-20")
    except ValueError as e:
        assert "figure src" in str(e)
    else:
        raise AssertionError("a malformed figure on a gated essay loaded silently")


def _committed_essays() -> list[tuple[str, dict]]:
    return [(p.stem, json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(site.ESSAYS_DIR.glob("*.json"))]


def test_every_committed_essay_label_has_its_explanation():
    """S74-8 B. A label with no text in ESSAY_LABELS renders as a bare word: the reader is told a
    standing caveat applies and not what it is."""
    essays = _committed_essays()
    assert len(essays) >= 7, [s for s, _ in essays]
    for slug, essay in essays:
        assert essay.get("labels"), slug
        for label in essay["labels"]:
            text = public_strings.ESSAY_LABELS.get(label)
            assert isinstance(text, str) and text.strip(), (slug, label)


def test_every_committed_receipt_has_member_date_and_a_web_url():
    """S74-8 B. _essay_receipts drops a receipt missing any of the three, silently, so a malformed
    receipt in a committed essay would vanish from the page instead of failing anywhere."""
    for slug, essay in _committed_essays():
        assert essay.get("receipts"), slug
        for i, receipt in enumerate(essay["receipts"]):
            assert str(receipt.get("member") or "").strip(), (slug, i)
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(receipt.get("date") or "")), (slug, i)
            assert re.match(r"https?://[^\s/]+\.[^\s/]+", str(receipt.get("url") or "")), (slug, i)
            assert site._safe_http_url(receipt["url"]), (slug, i)


def test_every_committed_essay_comes_due_on_its_own_date_with_its_figures():
    """S74-8 B. Each committed essay loads on its date and not the day before, and every figure it
    names is a committed file."""
    from datetime import date, timedelta
    for slug, essay in _committed_essays():
        day = essay["date"]
        before = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
        assert slug in {e["slug"] for e in site.load_essays(product_day=day)}, slug
        assert slug not in {e["slug"] for e in site.load_essays(product_day=before)}, slug
        for figure in site.essay_figures({**essay, "slug": slug}):
            assert (site.essay_figures_dir() / figure["name"]).is_file(), (slug, figure["name"])
        for text in [essay.get("title"), essay.get("dek"), *essay.get("body", [])]:
            assert "—" not in str(text or ""), slug


def test_load_essays_is_the_only_reader_of_the_essays_tree():
    """Every surface is gated because every surface reads through load_essays. A second reader of
    content/essays would be a second, ungated publication path."""
    root = Path(__file__).resolve().parent.parent
    readers = []
    for path in list((root / "pipeline").rglob("*.py")) + list((root / "scripts").rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "ESSAYS_DIR" in text or '"content" / "essays"' in text or "content/essays" in text:
            readers.append(path.relative_to(root).as_posix())
    assert readers == ["pipeline/site.py"], readers
    # Inside site.py the essays are listed in exactly two places, both through load_essays: the
    # import-time ESSAYS (which drives the nav) and the render-time reload in build_site.
    source = (root / "pipeline" / "site.py").read_text(encoding="utf-8")
    assert source.count("load_essays()") == 2
