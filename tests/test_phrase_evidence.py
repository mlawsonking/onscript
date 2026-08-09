"""D5 regression tests for copy-aligned, quorum-grounded peak-day evidence."""
from __future__ import annotations

import json
import io
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from pipeline import build, phrase_evidence, privacy, site


DAY = "2026-02-09"
NGRAM = "equal justice under law"
SLUG = "equal-justice"


def _phrase():
    return {
        "ngram": NGRAM, "slug": SLUG,
        "first_seen": {"date": DAY, "bioguide": "A000001"},
        "series": [{"day": DAY, "D": 5, "R": 0, "I": 0}],
    }


def _statement(i: int, *, text=None, party="D", joint=None, url=None):
    return {
        "id": f"s{i}", "lane": 1, "published_at": DAY, "syndicated": False,
        "joint_group": joint,
        "url": url or f"https://member{i}.house.gov/release",
        "text": text if text is not None else f"We demand {NGRAM} for every American.",
        "member": {"bioguide": f"B{i:06d}", "name": f"Member {i}",
                   "party": party, "state": "CA"},
    }


def _build(statements, *, cache_path=None):
    holder = tempfile.TemporaryDirectory()
    root = Path(holder.name)
    pdir = root / "phrases"
    pdir.mkdir()
    (pdir / f"{SLUG}.json").write_text(json.dumps(_phrase()), encoding="utf-8")
    cache = Path(cache_path) if cache_path else root / "cache.json"
    artifact, stats = phrase_evidence.build_phrase_evidence(
        statements, root, cache_path=cache, rmap={})
    return holder, root, cache, artifact, stats


def test_search_copy_promises_only_the_evidence_phrase_pages_can_deliver():
    html = site.phrase_search_body([])
    assert "members who carried it" not in html
    assert "at least three distinct offices" in html
    assert "peak-day source receipts" in html
    source = Path(site.__file__).read_text(encoding="utf-8")
    assert "first sayer, receipts" not in source


def test_quorum_requires_three_exactly_grounded_distinct_units():
    statements = [
        _statement(1), _statement(2), _statement(3),
        _statement(4, text="We demand equal justice. Under law, we will act."),
        _statement(5, text="We demand equal justice beyond law."),
    ]
    holder, _, _, artifact, _ = _build(statements)
    try:
        record = artifact["phrases"][SLUG]
        assert record["grounded_units"] == 3
        assert len(record["receipts"]) == 3
        assert "Peak-day evidence" in site.phrase_page_body(_phrase(), evidence=artifact)
    finally:
        holder.cleanup()


def test_below_quorum_writes_no_section_and_logs_the_omission():
    log = io.StringIO()
    with redirect_stdout(log):
        holder, _, _, artifact, stats = _build([_statement(1), _statement(2)])
    try:
        assert artifact["phrases"] == {}
        assert stats["omitted"] == 1
        assert "omitted" in log.getvalue() and "(<3)" in log.getvalue()
        assert "Peak-day evidence" not in site.phrase_page_body(_phrase(), evidence=artifact)
    finally:
        holder.cleanup()


def test_joint_release_family_counts_once():
    statements = [
        _statement(1, joint="joint:one"),
        _statement(2, joint="joint:one"),
        _statement(3, joint="joint:one"),
        _statement(4), _statement(5),
    ]
    holder, _, _, artifact, _ = _build(statements)
    try:
        assert artifact["phrases"][SLUG]["grounded_units"] == 3
    finally:
        holder.cleanup()


def test_slice_has_only_valid_source_metadata_and_no_quote_or_statement_text():
    statements = [_statement(1), _statement(2), _statement(3),
                  _statement(4, url="javascript:alert(1)")]
    holder, root, _, artifact, _ = _build(statements)
    try:
        stored = json.loads((root / "phrase-evidence.json").read_text(encoding="utf-8"))
        assert stored == artifact
        payload = json.dumps(stored)
        assert '"text"' not in payload and '"quote"' not in payload and '"statement"' not in payload
        for receipt in artifact["phrases"][SLUG]["receipts"]:
            assert set(receipt) == {"member", "party", "state", "date", "url"}
            assert receipt["url"].startswith(("http://", "https://"))
    finally:
        holder.cleanup()


def test_suppressed_phrase_produces_no_slice_or_evidentiary_section():
    original = privacy.is_suppressed
    privacy.is_suppressed = lambda text: NGRAM in str(text)
    try:
        holder, _, _, artifact, _ = _build([_statement(1), _statement(2), _statement(3)])
        try:
            assert artifact["phrases"] == {}
            fake = {"phrases": {SLUG: {"peak_day": DAY, "grounded_units": 3,
                    "counts": {"D": 3, "R": 0},
                    "receipts": [{"member": f"Member {i}", "party": "D", "state": "CA",
                                  "date": DAY, "url": f"https://m{i}.house.gov/r"}
                                 for i in range(3)]}}}
            assert site.phrase_evidence_body(_phrase(), evidence=fake) == ""
        finally:
            holder.cleanup()
    finally:
        privacy.is_suppressed = original


def test_suppressed_receipt_is_removed_before_the_slice_is_written():
    original = privacy.is_suppressed
    privacy.is_suppressed = lambda text: "blocked-source" in str(text)
    try:
        statements = [_statement(1), _statement(2), _statement(3),
                      _statement(4, url="https://blocked-source.house.gov/release")]
        holder, root, _, artifact, _ = _build(statements)
        try:
            record = artifact["phrases"][SLUG]
            assert record["grounded_units"] == 3
            payload = (root / "phrase-evidence.json").read_text(encoding="utf-8")
            assert "blocked-source" not in payload
        finally:
            holder.cleanup()
    finally:
        privacy.is_suppressed = original


def test_removed_source_invalidates_cache_and_removes_receipt():
    with tempfile.TemporaryDirectory() as td:
        cache = Path(td) / "cache.json"
        first_holder, _, _, first, first_stats = _build(
            [_statement(1), _statement(2), _statement(3), _statement(4)], cache_path=cache)
        try:
            second_holder, _, _, second, second_stats = _build(
                [_statement(1), _statement(2), _statement(3)], cache_path=cache)
            try:
                assert first["phrases"][SLUG]["grounded_units"] == 4
                assert second["phrases"][SLUG]["grounded_units"] == 3
                assert first_stats["cache_misses"] == 1 and second_stats["cache_misses"] == 1
                assert all(r["member"] != "Member 4" for r in second["phrases"][SLUG]["receipts"])
            finally:
                second_holder.cleanup()
        finally:
            first_holder.cleanup()


def test_copy_and_behavior_agree_below_and_at_quorum():
    copy_html = site.phrase_search_body([])
    below = site.phrase_page_body(_phrase(), evidence={"phrases": {}})
    record = {"peak_day": DAY, "grounded_units": 3, "counts": {"D": 3, "R": 0},
              "receipts": [{"member": f"Member {i}", "party": "D", "state": "CA",
                            "date": DAY, "url": f"https://m{i}.house.gov/r"} for i in range(3)]}
    at_quorum = site.phrase_page_body(_phrase(), evidence={"phrases": {SLUG: record}})
    assert "where at least three distinct offices" in copy_html.lower()
    assert "Peak-day evidence" not in below
    assert "Peak-day evidence" in at_quorum
    assert "Showing 3 of 3" in at_quorum
    assert "web.archive.org/web/20260209/" in at_quorum


def test_evidence_failure_cannot_cost_the_day_summary_or_the_run():
    """The optional evidence slice is downstream of, and fail-soft beside, the core day artifact."""
    holder = tempfile.TemporaryDirectory()
    root = Path(holder.name)
    (root / "phrases").mkdir()
    (root / "days").mkdir()
    ledger = {NGRAM: {
        "ngram": NGRAM, "n": 4, "df_weight": 1.0,
        "first_seen": {"date": DAY, "party": "D", "member": "B000001"},
        "daily": {DAY: {"D": 3, "R": 0, "members_D": ["B000001", "B000002", "B000003"],
                        "members_R": []}},
    }}
    original = phrase_evidence.build_phrase_evidence
    phrase_evidence.build_phrase_evidence = lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        result = build.build_derived(
            [_statement(1)], ledger, {"D": {DAY: 1.0}, "R": {DAY: 0.0}}, root,
            focus_day=DAY, coverage={"2026": {}},
        )
        assert result["focus_day_write"] == "written"
        assert (root / "days" / f"{DAY}.json").exists()
    finally:
        phrase_evidence.build_phrase_evidence = original
        holder.cleanup()


def test_peak_and_evidence_copy_reconciles_its_two_denominators():
    record = {"peak_day": DAY, "grounded_units": 5, "counts": {"D": 3, "R": 2},
              "receipts": [{"member": f"Member {i}", "party": "D" if i < 4 else "R",
                            "state": "CA", "date": DAY, "url": f"https://m{i}.house.gov/r"}
                           for i in range(1, 6)]}
    html = site.phrase_page_body(_phrase(), evidence={"phrases": {SLUG: record}})
    assert "largest count for either party" in html
    assert "across both parties on that same day" in html
