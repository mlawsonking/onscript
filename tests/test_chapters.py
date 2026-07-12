"""Tests for the Alexandria chapter-input layer (pipeline/chapters.py).

Locks the behavior of the BOUNDED nested-phrase collapse that replaced the O(n^2) full
collapse (the ~80-minute hang on the 2.77M-phrase ledger): correct top phrases, members-aware
nesting, monthly inputs, and that finalize_chapters tolerates monthly inputs (no `congress`
key). Pure functions — no network (roster stubbed), no API."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import chapters, config  # noqa: E402

chapters.roster.load = lambda *a, **k: {}  # hermetic: no mirror build


def _entry(daily: dict, first_date="2025-02-01", first_bio="A"):
    return {"daily": daily, "first_seen": {"date": first_date, "bioguide": first_bio}}


def _day(d_ct=0, d_mem=None, r_ct=0, r_mem=None):
    return {"D": d_ct, "members_D": d_mem or [], "R": r_ct, "members_R": r_mem or []}


# A synthetic ledger, all activity on one 119th-Congress day for party D.
DAY = "2026-06-30"          # -> 119th Congress
COVERAGE = {"2025": {"D": 2000, "R": 2000}, "2026": {"D": 2000, "R": 2000}}


def _ledger():
    L = {
        # peak 5, same members as its sub-phrase -> the sub-phrase must collapse away
        "born in the united states": _entry({DAY: _day(5, list("ABCDE"))}),
        "born in the united":        _entry({DAY: _day(5, list("ABCDE"))}),
        # longer, lower peak, subset members -> NOT a substring of the kept shorter one -> kept
        "born in the united states of america": _entry({DAY: _day(3, list("ABC"))}),
        # unrelated, peak 4 -> kept
        "protecting our democracy":  _entry({DAY: _day(4, list("FGHI"))}),
        # members-aware: sub-phrase whose members are NOT a subset of the longer one -> kept
        "we must act now": _entry({DAY: _day(5, list("ABCDE"))}),
        "we must act":     _entry({DAY: _day(4, list("ABCX"))}),  # X not in ABCDE -> not subset
    }
    # 500 junk phrases at exactly the sync floor (3) — the bound must keep this fast and must
    # not let junk crowd out the high-peak real phrases.
    for i in range(500):
        L[f"junk phrase number {i}"] = _entry({DAY: _day(3, ["A", "B", "C"])})
    return L


def _era_119_D(inputs):
    return next(i for i in inputs if i["id"] == "era-119-D")


def test_era_input_schema_and_sufficiency():
    inputs = chapters.build_era_inputs(_ledger(), COVERAGE)
    e = _era_119_D(inputs)
    assert e["kind"] == "era" and e["congress"] == 119 and e["party"] == "D"
    assert e["stats"]["statements"] == 4000 and e["sufficient"] is True   # 2025:2000 + 2026:2000
    assert e["fragments"] == [t["phrase"] for t in e["stats"]["top_phrases"]]
    assert len(e["stats"]["top_phrases"]) <= chapters.TOP_K


def test_nested_subphrase_with_subset_members_is_collapsed():
    inputs = chapters.build_era_inputs(_ledger(), COVERAGE)
    phrases = [t["phrase"] for t in _era_119_D(inputs)["stats"]["top_phrases"]]
    assert "born in the united states" in phrases          # the maximal high-peak phrase
    assert "born in the united" not in phrases              # subset-member sub-phrase -> collapsed


def test_nested_subphrase_with_divergent_members_is_kept():
    inputs = chapters.build_era_inputs(_ledger(), COVERAGE)
    phrases = [t["phrase"] for t in _era_119_D(inputs)["stats"]["top_phrases"]]
    assert "we must act now" in phrases
    assert "we must act" in phrases   # members {A,B,C,X} not <= {A,B,C,D,E} -> distinct signal, kept


def test_top_phrases_sorted_by_peak_desc():
    inputs = chapters.build_era_inputs(_ledger(), COVERAGE)
    top = _era_119_D(inputs)["stats"]["top_phrases"]
    peaks = [t["peak_members"] for t in top]
    assert peaks == sorted(peaks, reverse=True)
    assert top[0]["peak_members"] == 5
    # junk (peak 3) must not have crowded out the real high-peak phrases
    assert not any(t["phrase"].startswith("junk phrase") for t in top[:3])


def test_thin_era_is_insufficient():
    inputs = chapters.build_era_inputs(_ledger(), {"2025": {"D": 10}, "2026": {"D": 10}})
    # 118th Congress has no activity in our synthetic ledger -> thin/insufficient
    e = next(i for i in inputs if i["id"] == "era-118-D")
    assert e["sufficient"] is False and e["stats"]["coverage"] == "thin"


def test_monthly_inputs_and_finalize_tolerates_no_congress_key():
    ledger = _ledger()
    monthly = chapters.build_monthly_inputs(ledger)
    m = next((i for i in monthly if i["month"] == "2026-06" and i["party"] == "D"), None)
    assert m is not None and "congress" not in m       # monthly inputs carry no congress key
    assert m["kind"] == "month" and m["label"] == "2026-06"
    # finalize must not KeyError on a monthly input (regression: it read inp["congress"] directly,
    # which crashes for monthly). Exercised regardless of the sufficient/stub branch.
    import tempfile
    orig = chapters.CHAPTERS_DIR
    chapters.CHAPTERS_DIR = Path(tempfile.mkdtemp()) / "chapters"  # never touch real derived data
    try:
        summary = chapters.finalize_chapters([m], {m["id"]: "A neutral one-line chapter."})
    finally:
        chapters.CHAPTERS_DIR = orig
    assert summary["published"] + summary["failed"] + summary["stubbed"] == 1


def test_bounded_collapse_is_fast_on_a_wide_bucket():
    # 5000 distinct phrases in one bucket must not trigger the old O(n^2) blowup.
    import time
    L = {f"phrase alpha beta {i}": _entry({DAY: _day(3, ["A", "B", "C"])}) for i in range(5000)}
    L["dominant coordinated message here"] = _entry({DAY: _day(9, list("ABCDEFGHI"))})
    t = time.time()
    inputs = chapters.build_era_inputs(L, COVERAGE)
    assert time.time() - t < 5.0, "bounded collapse should be well under a second here"
    top = _era_119_D(inputs)["stats"]["top_phrases"]
    assert top[0]["phrase"] == "dominant coordinated message here"
