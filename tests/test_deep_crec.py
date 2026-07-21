"""Unit tests for the CREC ingest parser (docs/15 §D1). Locks the MODS attribution parse, the author
resolution, and the furniture stripper — validated against real GovInfo data (CREC-2001-01-03: 41
Extensions granules, 97% attributed) and frozen here with synthetic fixtures."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.deep import crec  # noqa: E402

_MODS = """<?xml version="1.0"?>
<mods xmlns="http://www.loc.gov/mods/v3" xmlns:xlink="http://www.w3.org/1999/xlink">
  <relatedItem type="constituent" ID="id-CREC-2001-01-03-pt1-PgE1">
    <extension>
      <granuleClass>EXTENSIONS</granuleClass>
      <accessId>CREC-2001-01-03-pt1-PgE1</accessId>
      <congMember bioGuideId="E000172" chamber="H" congress="107" party="R" role="SPEAKING" state="MO">
        <name type="authority-fnf">Jo Ann Emerson</name>
      </congMember>
    </extension>
  </relatedItem>
  <relatedItem type="constituent" ID="id-CREC-2001-01-03-pt1-PgD1">
    <extension>
      <granuleClass>DAILYDIGEST</granuleClass>
      <accessId>CREC-2001-01-03-pt1-PgD1</accessId>
    </extension>
  </relatedItem>
</mods>"""


def test_parse_granules_filters_class_and_reads_structured_attribution():
    grans = crec.parse_granules(_MODS.encode(), allow=("EXTENSIONS",))
    assert len(grans) == 1                                   # DAILYDIGEST filtered out
    g = grans[0]
    assert g["access_id"] == "CREC-2001-01-03-pt1-PgE1" and g["granule_class"] == "EXTENSIONS"
    m = g["congmembers"][0]
    assert m == {"bioguide": "E000172", "party": "R", "chamber": "H", "role": "SPEAKING",
                 "state": "MO", "congress": "107"}          # no name-parsing — structured from MODS


def test_extension_author_picks_speaking_and_skips_unattributed():
    g = crec.parse_granules(_MODS.encode())[0]
    a = crec.extension_author(g)
    assert a["bioguide"] == "E000172" and a["party"] == "R"
    assert crec.extension_author({"congmembers": []}) is None                       # unattributed -> None
    assert crec.extension_author({"congmembers": [{"bioguide": None, "party": "R"}]}) is None


def test_strip_furniture_removes_record_page_structure():
    html = ("<html><head><title>x</title></head><body><pre>\n"
            "[Congressional Record Volume 147, Number 1 (Wednesday, January 3, 2001)]\n"
            "[Extensions of Remarks]\n[Page E1]\n"
            "From the Congressional Record Online through the Government Publishing Office "
            "[<a href=\"https://www.gpo.gov\">www.gpo.gov</a>]\n\n[[Page E1]]\n\n\n"
            "                       THE NOTCH BABY ACT OF 2001\n"
            "                                 ______\n\n"
            "                          HON. JO ANN EMERSON\n"
            "  Mrs. EMERSON. Mr. Speaker, today I am introducing legislation to help seniors.\n"
            "</pre></body></html>")
    title, text = crec.strip_furniture(html)
    assert title == "THE NOTCH BABY ACT OF 2001"
    assert "[[Page" not in text and "[Congressional Record" not in text     # page furniture gone
    assert "Government Publishing Office" not in text                       # GPO line gone
    assert "______" not in text                                            # rule separator gone
    assert "introducing legislation to help seniors" in text               # the substance survives


def test_endpoints_are_the_verified_keyless_paths():
    assert crec.mods_url("CREC-2001-01-03").endswith("/metadata/pkg/CREC-2001-01-03/mods.xml")
    assert crec.granule_html_url("CREC-2001-01-03", "CREC-2001-01-03-pt1-PgE1") == \
        "https://www.govinfo.gov/content/pkg/CREC-2001-01-03/html/CREC-2001-01-03-pt1-PgE1.htm"


def test_crawl_manifest_survives_a_torn_final_line():
    """Resumability safety net: a hard-killed crawl can leave a partial final line in the manifest. The
    reader must skip it and load every prior (valid) checkpoint — else a resume would re-fetch what was
    already done (or crash)."""
    import tempfile
    from pipeline.deep import lanes
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write('{"id":"mods:CREC-2005-01-04","sha":"x","bytes":10}\n')
        f.write('{"id":"day-done:CREC-2005-01-04","sha":"done"}\n')
        f.write('{"id":"CREC-2005-01-04-pt1-PgE9","sha":  ')   # torn final line (crawl killed mid-write)
        path = f.name
    m = lanes.CrawlManifest(Path(path))
    Path(path).unlink()
    assert m.seen("mods:CREC-2005-01-04") and m.seen("day-done:CREC-2005-01-04")
    assert not m.seen("CREC-2005-01-04-pt1-PgE9")             # torn line skipped, resume re-fetches it


def test_published_date_is_iso_not_the_package_id():
    """Regression: the package id 'CREC-2001-01-03' is NOT the date. published_at/unit_date must be the
    ISO '2001-01-03' — else [:4] year/era logic reads 'CREC' and every year collapses to one window."""
    assert crec.pkg_date("CREC-2001-01-03") == "2001-01-03"
    g = crec.parse_granules(_MODS.encode())[0]
    stmt = crec.to_statement("CREC-2001-01-03", g, crec.extension_author(g), "T", "body")
    assert stmt["published_at"] == "2001-01-03" and stmt["unit_date"] == "2001-01-03"
    assert stmt["published_at"][:4] == "2001"                     # year extraction works


# --- the masked-HTML-error trap (docs/15 §D1.a, on the METADATA path) ----------------------------
# GovInfo serves "Page Not Found" as HTTP 200 with an HTML body for packages its own sitemap lists.
# Measured 2026-07-21: 10 days across 2013-2022, every one an identical 44,165-byte error page. The
# first 512 bytes of the real payload:
_ERROR_PAGE = (b'<!DOCTYPE html>\n<html lang="en" dir="ltr" prefix="content: '
               b'http://purl.org/rss/1.0/modules/content/">\n<head>\n<title>Page Not Found | GovInfo'
               b'</title>\n</head>\n<body>Sorry, the page you requested was not found.</body></html>')


def test_looks_like_mods_rejects_the_govinfo_error_page():
    """The kill-fixture. `urlopen` raises nothing (status is 200), so the PAYLOAD is the only signal —
    if this returns True the error page gets hash-manifested into the raw mirror as archival evidence
    AND cached, so every later resume reads it off disk and the day can never heal."""
    assert crec.looks_like_mods(b'<mods xmlns="http://www.loc.gov/mods/v3" version="3.3">')  # real: no decl
    assert crec.looks_like_mods(b'<?xml version="1.0"?>\n<mods/>')
    assert crec.looks_like_mods(b'\n  <mods/>')                       # leading whitespace tolerated
    assert not crec.looks_like_mods(_ERROR_PAGE)
    assert not crec.looks_like_mods(b"")
    assert not crec.looks_like_mods(b'<!doctype HTML><html><title>Page Not Found</title>')


class _FakeUpstream:
    """Run crawl_extensions against a fake GovInfo, rooted entirely inside `root`. Written without
    pytest fixtures because tests/run_tests.py calls every test with no arguments."""

    def __init__(self, root, payloads, days=("CREC-2019-01-03",)):
        self.root, self.payloads, self.days = Path(root), payloads, list(days)
        self.calls = []

    def __enter__(self):
        from pipeline.deep import lanes
        self._lanes = lanes
        self._saved = (lanes.DEEP_ROOT, lanes.POLITE["min_interval_s"],
                       crec.enumerate_days, crec._get)
        lanes.DEEP_ROOT = self.root
        lanes.POLITE["min_interval_s"] = 0
        crec.enumerate_days = lambda year: list(self.days)

        def _get(url, timeout=90):
            self.calls.append(url)
            return self.payloads(url)
        crec._get = _get
        return self

    def __exit__(self, *exc):
        (self._lanes.DEEP_ROOT, self._lanes.POLITE["min_interval_s"],
         crec.enumerate_days, crec._get) = self._saved
        return False

    def crawl(self):
        return crec.crawl_extensions([2019], progress=False)


def test_a_non_mods_payload_never_enters_the_mirror_and_settles_the_day():
    """A sitemap-listed day whose MODS 404s-as-200 must be recorded SETTLED-unavailable: nothing
    mirrored, and a resume must not re-fetch it. Counting it as 'pending' forever is what made the same
    10 days fail on every run for six days, and made 100% coverage unreachable by construction."""
    import tempfile
    from pipeline.deep import lanes
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with _FakeUpstream(root, lambda url: _ERROR_PAGE) as up:
            stats = up.crawl()
            assert stats["no_mods"] == 1 and stats["days"] == 0
            assert not list((root / "crec" / "raw" / "mods").rglob("*.mods.xml"))   # nothing mirrored
            man = lanes.CrawlManifest(root / "crec" / "state" / "crawl-manifest.jsonl")
            assert man.seen("day-nomods:CREC-2019-01-03")
            assert not man.seen("mods:CREC-2019-01-03")     # never recorded as a good fetch

            n = len(up.calls)
            up.crawl()                                      # resume
            assert len(up.calls) == n, "a settled-unavailable day must not be re-fetched every resume"


def test_a_poisoned_cache_entry_is_quarantined_not_deleted_and_the_day_heals():
    """Pre-validation runs wrote error pages into the mirror and manifested them as good. On the next
    pass that cache must be moved aside (the mirror is append-only evidence — what upstream actually
    served is part of the record) and the day re-attempted, not read from the poisoned copy forever."""
    import tempfile
    from pipeline.deep import lanes
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        mods_dir = root / "crec" / "raw" / "mods" / "2019"
        mods_dir.mkdir(parents=True)
        (mods_dir / "CREC-2019-01-03.mods.xml").write_bytes(_ERROR_PAGE)
        state = root / "crec" / "state"
        state.mkdir(parents=True)
        lanes.CrawlManifest(state / "crawl-manifest.jsonl").record(
            "mods:CREC-2019-01-03", "sha-of-an-error-page", len(_ERROR_PAGE))

        with _FakeUpstream(root, lambda url: _ERROR_PAGE) as up:
            stats = up.crawl()

        rejected = root / "crec" / "raw" / "mods" / "_rejected" / "2019" / "CREC-2019-01-03.mods.xml"
        assert rejected.exists() and rejected.read_bytes() == _ERROR_PAGE   # preserved, not destroyed
        assert not (mods_dir / "CREC-2019-01-03.mods.xml").exists()         # off the fetch-cache path
        assert stats["no_mods"] == 1
        assert lanes.CrawlManifest(state / "crawl-manifest.jsonl").seen("day-nomods:CREC-2019-01-03")


def test_a_valid_mods_day_still_crawls_normally():
    """Regression guard on the validation: the happy path must be untouched."""
    import tempfile
    from pipeline.deep import lanes

    def upstream(url):
        return _MODS.encode() if url.endswith("mods.xml") else b"<pre>Mr. Speaker, a real statement.</pre>"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with _FakeUpstream(root, upstream) as up:
            stats = up.crawl()
        assert stats["no_mods"] == 0 and stats["days"] == 1 and stats["granules"] == 1
        assert (root / "crec" / "raw" / "mods" / "2019" / "CREC-2019-01-03.mods.xml").exists()
        man = lanes.CrawlManifest(root / "crec" / "state" / "crawl-manifest.jsonl")
        assert man.seen("day-done:CREC-2019-01-03") and not man.seen("day-nomods:CREC-2019-01-03")
