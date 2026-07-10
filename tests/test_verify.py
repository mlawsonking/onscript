"""Tests for the deterministic citation verifier (§6.3) — the product's armor."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import verify  # noqa: E402


def test_is_verbatim_substring_and_whitespace_insensitive():
    src = "We will  protect Social Security   and Medicare for every senior."
    assert verify.is_verbatim("protect Social Security and Medicare", src)
    assert verify.is_verbatim("PROTECT social security", src)  # case-insensitive
    assert not verify.is_verbatim("protect social security benefits", src)  # invented word
    assert not verify.is_verbatim("", src)


def test_numbers_whitelist_blocks_invented_numbers():
    stats = '{"members": 41, "day": "2026-07-09"}'
    ok, off = verify.numbers_whitelisted("41 of us said it today.", stats)
    assert ok and not off
    ok, off = verify.numbers_whitelisted("We repeated it 87 times.", stats)  # 87 not in stats
    assert not ok and off == {"87"}
    # comma-normalization: 1,000 == 1000
    ok, _ = verify.numbers_whitelisted("We issued 1,000 statements.", '{"n": 1000}')
    assert ok


def test_talking_point_requires_three_distinct_members():
    statements = {
        "sha256:a": {"member": {"bioguide": "A"}, "text": "we demand a full account of what happened"},
        "sha256:b": {"member": {"bioguide": "B"}, "text": "give us a full account of the facts"},
        "sha256:c": {"member": {"bioguide": "C"}, "text": "the public deserves a full account of what happened"},
    }
    tp_ok = {
        "id": "x", "statements": ["sha256:a", "sha256:b", "sha256:c"],
        "fragments": [{"text": "a full account of what happened", "statement": "sha256:a"}],
    }
    ok, reasons = verify.verify_talking_point(tp_ok, statements)
    assert ok, reasons

    tp_two = dict(tp_ok, statements=["sha256:a", "sha256:b"])
    ok, reasons = verify.verify_talking_point(tp_two, statements)
    assert not ok and any("quorum" in r for r in reasons)


def test_talking_point_rejects_non_verbatim_fragment():
    statements = {"sha256:a": {"member": {"bioguide": "A"}, "text": "we will protect the border"},
                  "sha256:b": {"member": {"bioguide": "B"}, "text": "we will protect the border"},
                  "sha256:c": {"member": {"bioguide": "C"}, "text": "we will protect the border"}}
    tp = {"id": "x", "statements": ["sha256:a", "sha256:b", "sha256:c"],
          "fragments": [{"text": "seal the border completely", "statement": "sha256:a"}]}
    ok, reasons = verify.verify_talking_point(tp, statements)
    assert not ok and any("non-verbatim" in r for r in reasons)


def test_verify_day_drops_bad_claims_and_flags_bad_numbers():
    statements = {f"sha256:{c}": {"member": {"bioguide": c}, "text": "we will protect the border today"}
                  for c in "ABC"}
    good = {"id": "g", "statements": ["sha256:A", "sha256:B", "sha256:C"],
            "fragments": [{"text": "protect the border", "statement": "sha256:A"}]}
    bad = {"id": "b", "statements": ["sha256:A"],  # <3 members
           "fragments": [{"text": "protect the border", "statement": "sha256:A"}]}
    report = verify.verify_day({"composite": "3 of us spoke."}, [good, bad], statements,
                               stats_blob='{"members": 3}')
    assert report["claims_published"] == 1
    assert report["claims_dropped"] == 1
    assert report["daily_line_ok"] and report["failed"] == 0
