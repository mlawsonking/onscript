"""S74-17 Package E (R-74.25): the Concordance distribution is computed over every member with
statements in the window; only naming is gated at three distinct receipts. The flag stays off.
"""
from __future__ import annotations

from pipeline import build

PHRASES = ["protect social security benefits", "defend affordable health care",
           "expand rural broadband access"]


def _stmt(bio, party, text, day):
    return {"id": f"{bio}-{day}-{len(text)}", "lane": 1, "published_at": day, "congress": 119,
            "url": f"https://{bio.lower()}.house.gov/{day}", "text": text,
            "member": {"bioguide": bio, "party": party, "state": "TX", "chamber": "house",
                       "name": f"Rep. {bio}"}}


def test_a_member_below_the_gate_is_in_the_distribution_and_not_named():
    days = [f"2026-06-{i:02d}" for i in range(1, 5)]
    named = [_stmt("A", "D", f"today we will {PHRASES[i % 3]}", d) for i, d in enumerate(days)]
    zero = [_stmt("Z", "D", "an unrelated statement about roads", d) for d in days]       # index 0
    two = [_stmt("B", "R", f"today we will {PHRASES[i % 2]}", d) for i, d in enumerate(days)]  # 2 receipts
    res = build.build_concordance(named + zero + two, {p: {"peak_units": 20} for p in PHRASES},
                                  min_statements=1, roster_map={}, is_final=lambda d: True)
    assert [m["bioguide"] for m in res["members"]] == ["A"]
    d, r = res["distribution"]["D"], res["distribution"]["R"]
    assert d == {"members": 2, "mean": 0.5, "median": 0.5, "share_above_half": 0.5}
    assert r == {"members": 1, "mean": 1.0, "median": 1.0, "share_above_half": 1.0}
    assert res["counts"]["excluded_below_receipts"] == 2
