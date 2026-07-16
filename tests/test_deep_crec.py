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
