"""Tests for A3 normalize: dedupe, syndication, exact + near-identical joint-collapse (§11 trap 2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import normalize  # noqa: E402


def _rec(url, text, bio, party="Democrat", date="2026-07-09"):
    return {"url": url, "text": text, "title": "t", "date": date,
            "member": {"bioguide_id": bio, "party": party, "state": "TX", "chamber": "House"}}


def test_dedupe_by_id():
    recs = [_rec("u1", "identical body text", "A"), _rec("u1", "identical body text", "A")]
    out = normalize.normalize_records(recs, run_id="t")
    assert len(out) == 1


def test_exact_joint_collapse():
    body = "We stand together to demand a full and independent investigation into this matter now."
    recs = [_rec("u1", body, "A"), _rec("u2", body, "B"), _rec("u3", body, "C")]
    out = normalize.normalize_records(recs, run_id="t")
    groups = {s["joint_group"] for s in out}
    assert len(groups) == 1 and next(iter(groups)) is not None
    assert all(s["joint_group"].startswith("joint:") for s in out)


def test_near_identical_delegation_collapse():
    # Three delegation letters ~90% identical (only the lead name differs) -> one unit.
    base = ("Today we the members of the Texas delegation write to demand an immediate fully "
            "independent and transparent investigation into the killing and a full account of "
            "what happened and real accountability for everyone involved in this operation now")
    recs = [
        _rec("u1", "Representative Alpha said: " + base, "A"),
        _rec("u2", "Representative Beta said: " + base, "B"),
        _rec("u3", "Representative Gamma said: " + base, "C"),
    ]
    out = normalize.normalize_records(recs, run_id="t")
    groups = {s["joint_group"] for s in out}
    assert len(groups) == 1 and next(iter(groups)).startswith("njoint:"), \
        f"expected one near-joint group, got {groups}"


def test_distinct_statements_are_not_collapsed():
    recs = [
        _rec("u1", "We must secure the border and finish building the wall immediately this year.", "A", "Republican"),
        _rec("u2", "Healthcare costs are crushing families and we will lower prescription drug prices.", "B"),
    ]
    out = normalize.normalize_records(recs, run_id="t")
    assert all(s["joint_group"] is None for s in out)


def test_syndication_flag():
    recs = [_rec("u1", "Originally published in the Houston Chronicle. Our economy is strong today.", "A")]
    out = normalize.normalize_records(recs, run_id="t")
    assert out[0]["syndicated"] is True


def test_party_and_chamber_normalized():
    out = normalize.normalize_records([_rec("u1", "some political content here today friends", "A", "Republican")],
                                      run_id="t")
    assert out[0]["member"]["party"] == "R"
    assert out[0]["member"]["chamber"] == "house"
    assert out[0]["lane"] == 1 and out[0]["copyright_basis"] == "usc105"
