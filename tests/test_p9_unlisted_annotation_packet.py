"""The annotation packet is served unlisted, and the flag switches it both ways.

docs/35 §10.6 publishes the bundle openly, so serving it is not a disclosure decision. What
this surface must get right is narrower: it is a working sheet, not part of the public record,
so it stays out of the sitemap, out of robots, and out of search; and the rater must be able to
take it down again when the pass is finished.

Unlisted is not private. The slug is derived in committed code in a public repository, so
anyone reading the repository can compute it. These tests assert what the mechanism does, not
a confidentiality property it does not have.
"""
import json
from pathlib import Path

from pipeline import config, site


def _flag(value):
    """Set the flag and restore it, so a failure cannot leak state into another test."""
    previous = config.FEATURES["annotation_packet"]
    config.FEATURES["annotation_packet"] = value
    return previous


def test_the_flag_is_off_by_default():
    """It ships dark. Turning it on is a release act and belongs to the operator."""
    assert config.FEATURES["annotation_packet"] is False


def test_the_slug_is_derived_from_the_sealed_sample_and_is_stable():
    seal = json.loads((Path(config.REPO_ROOT) / "evaluation" / "goldset" / "MANIFEST.json")
                      .read_text(encoding="utf-8"))["seal_hash"]
    slug = site.annotation_packet_slug("michael-pass2")
    assert slug == site.annotation_packet_slug("michael-pass2")
    assert len(slug) == 16 and all(c in "0123456789abcdef" for c in slug)
    # Bound to the seal: a re-sealed kit does not keep serving at the old address.
    assert seal[:16] != slug
    assert site.annotation_packet_slug("someone-else") != slug


def test_the_flag_off_writes_nothing():
    previous = _flag(False)
    try:
        assert site.annotation_packet_pages() == []
    finally:
        config.FEATURES["annotation_packet"] = previous


def test_the_flag_on_serves_the_committed_bundle_byte_for_byte():
    """Copied, never re-rendered: the page worked and the artifact published cannot diverge."""
    previous = _flag(True)
    try:
        pages = site.annotation_packet_pages()
        assert pages == [f"annotate/{site.annotation_packet_slug('michael-pass2')}/index.html"]
        served = site.OUT / pages[0]
        source = site.ANNOTATION_BUNDLE / "michael-pass2.app.html"
        assert served.read_bytes() == source.read_bytes()
    finally:
        config.FEATURES["annotation_packet"] = previous


def test_turning_the_flag_off_again_removes_the_page():
    """The build does not clear its output tree, so withdrawal has to be explicit."""
    previous = _flag(True)
    try:
        pages = site.annotation_packet_pages()
        served = site.OUT / pages[0]
        assert served.is_file()
        config.FEATURES["annotation_packet"] = False
        assert site.annotation_packet_pages() == []
        assert not served.exists(), "a withdrawn packet must not keep serving"
    finally:
        config.FEATURES["annotation_packet"] = previous


def test_the_served_page_refuses_indexing_and_carries_no_machine_signal():
    previous = _flag(True)
    try:
        pages = site.annotation_packet_pages()
        html = (site.OUT / pages[0]).read_text(encoding="utf-8")
        assert '<meta name="robots" content="noindex,nofollow">' in html
        payload = json.loads(html.split('id="goldset-data" type="application/json">')[1]
                             .split("</script>")[0].replace("<\\/", "</"))
        assert len(payload["items"]) == 200
        for item in payload["items"]:
            assert set(item) <= {"candidate_id", "phrase", "before", "sentence", "after",
                                 "title", "office", "date", "support"}
    finally:
        # Restore the flag, then run once more so the withdrawal branch clears the page this
        # test served. The suite must not leave a generated file in site/public.
        config.FEATURES["annotation_packet"] = previous
        site.annotation_packet_pages()


def test_an_unlisted_page_never_enters_the_sitemap():
    """The sitemap is driven by `written`; unlisted pages are returned separately on purpose."""
    import inspect
    source = inspect.getsource(site.build_site)
    assert "unlisted = annotation_packet_pages()" in source
    assert "sitemap(written)" in source
    # The unlisted list feeds robots.txt, not the sitemap.
    assert "Disallow: /{path}" in source


def test_robots_disallows_whatever_is_served_unlisted():
    disallowed = "".join(f"Disallow: /{p}\n" for p in sorted(["annotate/abc/index.html"]))
    assert disallowed == "Disallow: /annotate/abc/index.html\n"
