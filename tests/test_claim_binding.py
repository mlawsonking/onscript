"""P0 fixtures for docs/28: one support phrase, one count, one quote, one receipt set."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import boilerplate, cluster, distill, privacy, run_assemble, site, verify  # noqa: E402


def _statement(sid: str, bio: str, party: str, text: str, *, joint=None) -> dict:
    return {
        "id": sid, "text": text, "published_at": "2026-07-23", "joint_group": joint,
        "member": {"bioguide": bio, "party": party, "state": "VA"},
        "url": f"https://{bio.lower()}.house.gov/statement",
    }


def _annotated(statement: dict, fragment: str | None = None) -> dict:
    return {
        "text": fragment or statement["text"], "topics": ["other"],
        "statement": statement["id"], "joint_group": statement.get("joint_group"),
        "bioguide": statement["member"]["bioguide"], "source_text": statement["text"],
    }


def _bridged_fixture(party: str = "R"):
    statements: dict[str, dict] = {}
    annotated: list[dict] = []
    for i in range(5):
        sid, bio = f"ndaa-{i}", f"N{i}"
        text = "Our colleagues in demanding the national defense authorization act spoke today."
        statements[sid] = _statement(sid, bio, party, text)
        annotated.append(_annotated(statements[sid]))
    for i in range(4):
        sid, bio = f"trade-{i}", f"T{i}"
        text = "Our colleagues in demanding the stop insider trading act spoke today."
        statements[sid] = _statement(sid, bio, party, text)
        annotated.append(_annotated(statements[sid]))
    roster = {s["member"]["bioguide"]: {
        "name": f"Member {s['member']['bioguide']}", "party": party, "state": "VA"
    } for s in statements.values()}
    return annotated, statements, roster


def _bound_bridge(party: str = "R"):
    annotated, statements, roster = _bridged_fixture(party)
    tps = cluster.cluster_day(party, "2026-07-23", annotated, statements_by_id=statements)
    assert len(tps) == 1
    published, dropped, rejected = run_assemble._screen_talking_points(tps, statements, roster)
    assert dropped == 0 and rejected == [] and len(published) == 1
    return published[0], statements, roster


def test_bridged_ndaa_and_insider_topics_publish_only_the_support_set():
    tp, statements, _roster = _bound_bridge()
    assert tp["label"] == "defense authorization act spoke today"
    assert tp["member_count"] == 5
    assert len(tp["statements"]) == 5
    assert verify.key_carrying_units(tp, statements) == {f"N{i}" for i in range(5)}
    assert all(boilerplate.contains_gram(f["text"], tp["label"]) for f in tp["fragments"])
    assert "stop insider trading" not in json.dumps(tp)


def test_component_count_cannot_return_as_the_public_numerator():
    tp, statements, _roster = _bound_bridge()
    mutated = {**tp, "member_count": 9}
    ok, reasons = verify.verify_talking_point(mutated, statements)
    assert not ok
    assert any("support-count" in reason for reason in reasons)


def test_quote_selection_cannot_escape_the_support_phrase():
    tp, _statements, _roster = _bound_bridge()
    contaminated = {
        **tp,
        "fragments": [
            {"text": "the stop insider trading act", "statement": "trade-x"},
            {"text": f"we carried {tp['label']}", "statement": "ndaa-0"},
        ],
    }
    stats = distill.build_stats("R", "2026-07-23", 9, [contaminated], None)
    quote = stats["talking_points"][0]["quote"]
    assert boilerplate.contains_gram(quote, tp["label"])
    assert "stop insider trading" not in quote


def test_citations_cannot_escape_the_support_phrase():
    tp, statements, roster = _bound_bridge()
    fragments = []
    for sid in tp["statements"]:
        fragments.append({"text": "voted in favor of an unrelated measure", "statement": sid})
        fragments.append({"text": f"we carried {tp['label']} exactly", "statement": sid})
    contaminated = {**tp, "fragments": fragments}
    citations = run_assemble._citations(contaminated, statements, roster)
    assert len(citations) == 3
    assert all(boilerplate.contains_gram(c["quote"], tp["label"]) for c in citations)


def test_combined_pool_grounding_cannot_bind_the_wrong_count_to_a_quote():
    stats = {
        "party": "R", "day": "2026-07-23", "statements": 9, "sync_min": 3,
        "top_phrase": None,
        "talking_points": [
            {"label": "the national defense authorization act", "members": 5,
             "quote": "the national defense authorization act", "topics": []},
            {"label": "the stop insider trading act", "members": 4,
             "quote": "the stop insider trading act", "topics": []},
        ],
    }
    composite = '5 of us carried "the stop insider trading act".'
    ok, reasons = verify.verify_daily_line(
        {"composite": composite}, json.dumps(stats),
        fragments=[tp["quote"] for tp in stats["talking_points"]], stats=stats,
    )
    assert not ok
    assert any("unbound talking-point quotes" in reason for reason in reasons)


def test_below_quorum_support_is_dropped_and_logged_for_both_parties():
    for party in ("D", "R"):
        statements = {
            "a": _statement("a", "A", party, "Our colleagues in demanding clean water protections spoke today."),
            "b": _statement("b", "B", party, "Our colleagues in demanding clean water protections spoke today."),
            "c": _statement("c", "C", party, "Our colleagues in demanding lower taxes for families spoke today."),
        }
        annotated = [_annotated(s) for s in statements.values()]
        tps = cluster.cluster_day(party, "2026-07-23", annotated, statements_by_id=statements)
        assert len(tps) == 1 and tps[0]["member_count"] == 2
        roster = {bio: {"name": bio, "party": party, "state": "VA"} for bio in "ABC"}
        published, dropped, rejected = run_assemble._screen_talking_points(tps, statements, roster)
        assert published == [] and dropped == 1
        assert len(rejected) == 1 and rejected[0]["reason"] == boilerplate.REJECT_FAMILY_QUORUM
        assert rejected[0]["member_count"] == 2


def test_joint_release_counts_once_in_the_support_set():
    phrase = "we must protect our public lands today"
    statements = {
        "a": _statement("a", "A", "D", phrase, joint="joint:lands"),
        "b": _statement("b", "B", "D", phrase, joint="joint:lands"),
        "c": _statement("c", "C", "D", phrase),
        "d": _statement("d", "D", "D", phrase),
    }
    tp = cluster.cluster_day(
        "D", "2026-07-23", [_annotated(s) for s in statements.values()],
        statements_by_id=statements,
    )[0]
    assert tp["member_count"] == 3
    assert verify.key_carrying_units(tp, statements) == {"joint:lands", "C", "D"}


def test_privacy_filter_sees_the_corrected_label_and_quote_surface():
    phrase = "we protect our public lands today"
    statements = {
        sid: _statement(sid, bio, "D", f"{phrase}. <private-individual-A>")
        for sid, bio in (("a", "A"), ("b", "B"), ("c", "C"))
    }
    annotated = [_annotated(s) for s in statements.values()]
    tp = cluster.cluster_day("D", "2026-07-23", annotated, statements_by_id=statements)[0]
    stats = distill.build_stats("D", "2026-07-23", 3, [tp], None)
    assert stats["talking_points"][0]["label"] == tp["label"]
    assert boilerplate.contains_gram(stats["talking_points"][0]["quote"], tp["label"])
    assert privacy.filter_stats(stats)[1] == 1
    published, dropped, rejected = run_assemble._screen_talking_points([tp], statements, {})
    assert published == [] and dropped == 1 and rejected == []


def test_receipt_header_stats_and_carrier_count_are_identical():
    tp, statements, _roster = _bound_bridge()
    stats = distill.build_stats("R", "2026-07-23", 9, [tp], None)
    carriers = len(verify.key_carrying_units(tp, statements))
    assert tp["member_count"] == stats["talking_points"][0]["members"] == carriers == 5
    html = site.receipts_strip("R", [tp], caucus=272)
    assert '<span class="rcount">5 members&rsquo;</span>' in html
    assert "phrase shown 3/3" in html


def _historical_day(bound: bool) -> dict:
    label = "the national defense authorization act"
    quote = label if bound else "the stop insider trading act"
    citation_quote = f"we passed {label} today" if bound else "announced house passage of the fiscal year"
    fragments = [{"text": f"we passed {label} today", "statement": f"s{i}"} for i in range(3)]
    if not bound:
        fragments.append({"text": quote, "statement": "trade"})
    citations = [
        {"member": f"Member {i}", "party": "R", "state": "VA", "date": "2026-07-22",
         "url": f"https://m{i}.house.gov/source", "quote": citation_quote}
        for i in range(3)
    ]
    tp = {"label": label, "member_count": 3, "fragments": fragments,
          "citations": citations, "topics": ["other"]}
    stat_tp = {"label": label, "members": 3, "quote": quote, "topics": ["other"]}
    return {
        "day": "2026-07-22" if not bound else "2026-07-23",
        "daily_lines": {"R": {
            "composite": f'3 of us carried "{quote}".', "generator": "deterministic",
            "verifier": {"checked": True, "passed": True},
            "stats": {"party": "R", "day": "2026-07-22", "statements": 3,
                      "sync_min": 3, "top_phrase": None, "talking_points": [stat_tp]},
        }},
        "talking_points": {"R": [tp]},
    }


def test_historical_correction_note_marks_only_the_pre_fix_mismatch():
    bad = site.daily_line_panel("R", _historical_day(False), caucus=272)
    assert '3 of us carried &quot;the stop insider trading act&quot;' in bad
    assert "This stored count overstates support for the quoted phrase" in bad
    assert "../methodology.html#corrections" in bad

    good = site.daily_line_panel("R", _historical_day(True), caucus=272)
    assert "This stored count overstates support for the quoted phrase" not in good
    assert "phrase shown 3/3" in good


def test_append_only_correction_entry_covers_the_ruled_window_and_measures():
    path = Path(__file__).resolve().parent.parent / "data" / "reference" / "corrections.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    row = next(r for r in rows if r.get("logged") == "2026-07-23")
    assert row["day"] == "2026-07-15 through 2026-07-23"
    assert "2 of 38" in row["description"] and "14 of 38" in row["description"]
    assert "28 of 63" in row["description"]
    assert "Stored day records, composite prose, and the signed post archive remain unchanged" in row["resolution"]
