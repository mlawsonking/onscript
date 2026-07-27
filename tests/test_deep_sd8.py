"""SD.8 instrument-concordance decision logic - failure fixtures (docs/12 §1.12).

The metric must not touch real data until it passes a synthetic corpus with a known injected answer:
a null (equal naming both parties) must NOT read as CONFIRM or REFUTE, and an opposite-direction corpus
must REFUTE, not confirm. Drives the pure `concordance()` with floor=2 so a handful of rows per cell
exercise the frozen decision rule (docs/12 §1) without the 200/cell power floor.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "deep"))

import sd8_concordance as SD8  # noqa: E402
from pipeline import config  # noqa: E402

PRES = json.loads((config.REFERENCE / "search" / "presidents.json").read_text(encoding="utf-8"))
CHAMBERS = json.loads((config.REFERENCE / "search" / "chambers-control.json").read_text(encoding="utf-8"))


def _stmt(year, party, text):
    congress = 113 + (year - 2013) // 2      # 2013/14->113 ... 2025/26->119
    return {"published_at": f"{year}-06-15", "member": {"party": party}, "congress": congress,
            "title": "t", "text": text}


def _corpus(direction):
    """direction in {'out','equal','in'}: which party names the sitting president more, every year."""
    cc = CHAMBERS["by_congress"]
    out = []
    for year in range(2013, 2027):
        tok, _ = SD8.sitting_president(PRES, year)
        cong = str(113 + (year - 2013) // 2)
        potus = cc[cong]["potus"]
        out_party = "D" if potus == "R" else "R"
        heavy = (tok + " ") * 5 + "policy words follow here"     # token-rich
        light = "policy words follow here with none"             # no name
        equal = (tok + " ") * 3 + "policy words here"            # identical both sides
        for party in ("D", "R"):
            for _ in range(3):                                   # 3 >= floor(2) per party-year
                if direction == "equal":
                    text = equal
                elif (direction == "out") == (party == out_party):
                    text = heavy
                else:
                    text = light
                out.append(_stmt(year, party, text))
    return out


def test_positive_control_confirms_when_out_party_names_more():
    res = SD8.concordance(_corpus("out"), PRES, CHAMBERS, floor=2)
    assert res["agreement_share"] == 1.0
    assert res["both_eras_majority"] is True
    assert res["verdict"] == "CONFIRM"


def test_a_null_equal_corpus_does_not_confirm_or_refute():
    """§1.12 kill fixture: equal naming carries NO directional signal. It must land HELD - neither a
    false CONFIRM (the coverage/tribute confound the study exists to catch) nor a REFUTE (a null is
    not a contradiction)."""
    res = SD8.concordance(_corpus("equal"), PRES, CHAMBERS, floor=2)
    assert res["agreement_share"] == 0.0
    assert res["contradiction_share"] == 0.0
    assert res["verdict"] == "HELD"


def test_opposite_direction_refutes_not_confirms():
    res = SD8.concordance(_corpus("in"), PRES, CHAMBERS, floor=2)
    assert res["contradiction_share"] == 1.0
    assert res["verdict"] == "REFUTE"


def test_power_floor_leaves_a_thin_year_unscored():
    """A year with < floor statements/party is UNSCORED and disclosed, never silently counted."""
    corpus = [s for s in _corpus("out")
              if not (s["published_at"].startswith("2013") and s["member"]["party"] == "R")]
    corpus.append(_stmt(2013, "R", "policy only"))   # exactly one 2013-R -> below floor=2
    res = SD8.concordance(corpus, PRES, CHAMBERS, floor=2)
    assert 2013 in res["per_year"]
    assert res["per_year"][2013]["scored"] is False
    assert 2013 not in res["scored_years"]
