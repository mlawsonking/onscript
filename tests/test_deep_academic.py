"""Unit tests for the academic-archive (Grimmer) ingester (docs/15 §D3). Locks the filename→date/surname
parse — validated on the real corpus (72,635 statements, 112/114 dirs mapped, every year 2004-2008
PASSES the symmetry audit). Network-free (the roster/senator-mapping is validated live, not here)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.deep import academic as AC  # noqa: E402


def test_parse_filename_extracts_iso_date_and_surname():
    assert AC.parse_filename("10Apr2007akaka175.txt") == ("2007-04-10", "akaka")
    assert AC.parse_filename("1Jan2005reid3.txt") == ("2005-01-01", "reid")
    assert AC.parse_filename("31Dec2006BenNelson12.txt") == ("2006-12-31", "bennelson")


def test_parse_filename_rejects_junk():
    assert AC.parse_filename(".DS_Store") is None
    assert AC.parse_filename("readme.txt") is None
    assert AC.parse_filename("10Xyz2007akaka.txt") is None      # bad month
    assert AC.parse_filename("SenateScripts") is None
