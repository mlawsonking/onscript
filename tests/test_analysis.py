"""Art. VI: the committed analysis artifacts (citations*.json, era_fingerprints.json) must be
reproducible from committed code. These tests prove the promoted generators are (a) import-safe —
importing them runs NO generation and touches NO X:/network — and (b) correct on synthetic data.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import must be side-effect-free (no top-level scan/generation). If these run on import, the
# suite would hang or fail reaching X:; that they import cleanly is half the Art. VI guarantee.
from scripts.analysis import citations, citations_era, era_fp2  # noqa: E402


def test_pure_helpers():
    assert citations.norm("  The  BORDER   Wall ") == "the border wall"
    assert citations_era.era_months("2013-14") == [f"2013-{m:02d}" for m in range(1, 13)] + \
        [f"2014-{m:02d}" for m in range(1, 13)]
    assert era_fp2.is_proc("of the united states") is True
    assert era_fp2.is_proc("border wall funding") is False
    # collapse keeps the maximal phrase, drops a nested sub-phrase
    rows = [(2.0, 30, "border wall funding"), (1.0, 20, "border wall")]
    kept = era_fp2.collapse(rows, k=10)
    assert [ng for _, _, ng in kept] == ["border wall funding"]


def test_citations_build_finds_verbatim_party_matched_citation():
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td)
        (raw / "2017-05.jsonl").write_text(
            json.dumps({"member": {"name": "Jane Doe", "bioguide_id": "D1", "party": "Republican",
                                   "state": "CA"}, "date": "2017-05-04",
                        "url": "https://doe.house.gov/x", "text": "I support the american health care act today.",
                        "title": "t"}) + "\n"
            # party mismatch — must NOT count even though the phrase matches:
            + json.dumps({"member": {"name": "Al Roe", "bioguide_id": "X9", "party": "Democrat"},
                          "date": "2017-05-04", "url": "https://roe.house.gov/y",
                          "text": "the american health care act is bad", "title": "t"}) + "\n",
            encoding="utf-8",
        )
        res = citations.build_citations(
            targets=[("AHCA", "american health care act", "R", ["2017-05"])], raw_dir=raw)
        row = res["AHCA"]
        assert row["n_citations"] == 1  # only the Republican, verbatim match
        assert row["citations"][0]["url"] == "https://doe.house.gov/x"


def test_era_fingerprints_build_excludes_procedural_and_keeps_content():
    # minimal synthetic ledger: one content phrase + one procedural phrase in the 115th (2017).
    ledger = {
        "border wall funding": {"daily": {"2017-05-01": {"D": 1200}}},
        "of the united states": {"daily": {"2017-05-01": {"D": 2000}}},  # procedural -> excluded
    }
    out = era_fp2.build(ledger)
    assert "115-D" in out
    phrases = [t["phrase"] for t in out["115-D"]["top"]]
    assert "border wall funding" in phrases
    assert "of the united states" not in phrases
