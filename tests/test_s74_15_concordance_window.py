"""S74-15 Package 4: the Concordance says only what it can support (the flag stays off).

(a) The window starts at config.STAGE1_EPOCH and ends at the last FINAL day; a statement outside it
never enters the index, so an impossible window is unreachable where it is computed (docs/37 rule 17).
(b) A member is named only with CONCORDANCE_RECEIPTS_MAX receipts on that many distinct phrases;
otherwise the row is omitted and counted in aggregate. No receipt phrase repeats.
"""
from __future__ import annotations

from pipeline import build, config

PHRASES = ["protect social security benefits", "defend affordable health care",
           "expand rural broadband access", "reform student loan debt"]


def _stmt(bio, text, day, party="D"):
    return {"id": f"{bio}-{day}-{len(text)}", "lane": 1, "published_at": day, "congress": 119,
            "url": f"https://{bio.lower()}.house.gov/{day}", "text": text,
            "member": {"bioguide": bio, "party": party, "state": "TX", "chamber": "house",
                       "name": f"Rep. {bio}"}}


def _led(peak=20):
    return {p: {"peak_units": peak} for p in PHRASES}


def test_the_window_starts_at_the_epoch_and_ends_at_the_last_final_day():
    epoch = config.STAGE1_EPOCH
    stmts = ([_stmt("A", f"today we will {p}", "2025-01-01") for p in PHRASES]       # pre-epoch
             + [_stmt("A", f"today we will {p}", f"2026-06-0{i + 1}") for i, p in enumerate(PHRASES)]
             + [_stmt("A", "today we will protect social security benefits", "2026-06-09")])
    finals = {"2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"}          # 06-09 not final yet
    res = build.build_concordance(stmts, _led(), min_statements=1, roster_map={},
                                  is_final=lambda d: d in finals)
    assert res["window"] == {"start": "2026-06-01", "end": "2026-06-04"}
    assert res["window"]["start"] >= epoch
    [a] = res["members"]
    assert a["statements"] == 4                       # neither the pre-epoch nor the unfinished day
    assert all(epoch <= r["date"] <= "2026-06-04" for r in a["receipts"])
    # Nothing final: no window at all, never a guessed one.
    none = build.build_concordance(stmts, _led(), min_statements=1, roster_map={},
                                   is_final=lambda d: False)
    assert none["window"] == {"start": None, "end": None} and none["members"] == []


def test_a_member_needs_three_distinct_receipts_to_be_named_and_none_repeats():
    days = [f"2026-06-{i:02d}" for i in range(1, 13)]
    # B uses only two distinct phrases, many times: never three receipts, so never named.
    two = [_stmt("B", f"today we will {PHRASES[i % 2]}", d) for i, d in enumerate(days)]
    # C uses three distinct phrases.
    three = [_stmt("C", f"today we will {PHRASES[i % 3]}", d) for i, d in enumerate(days)]
    res = build.build_concordance(two + three, _led(), min_statements=1, roster_map={},
                                  is_final=lambda d: True)
    named = {m["bioguide"]: m for m in res["members"]}
    assert "B" not in named and res["counts"]["excluded_below_receipts"] == 1
    c = named["C"]
    assert len(c["receipts"]) == config.CONCORDANCE_RECEIPTS_MAX
    assert len({r["phrase"] for r in c["receipts"]}) == len(c["receipts"])
    assert res["counts"]["members_seen"] == 2 and res["counts"]["named"] == 1
    assert res["window_rule"] == "STAGE1_EPOCH through the last final day"
