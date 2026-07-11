"""Tests for the LLM-layer modules (extract, cluster, distill) + neutrality hashes.
Pure functions only — no network, no cache side-effects, no API."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import cluster, distill, extract, ops, verify  # noqa: E402

_TAX = [{"id": "immigration", "seeds": ["born", "citizen", "immigration"]}, {"id": "other", "seeds": []}]


def _stmt(sid, text, bio, party="D"):
    return {"id": f"sha256:{sid}", "text": text, "published_at": "2026-06-30", "lane": 1,
            "syndicated": False, "member": {"bioguide": bio, "party": party}}


def test_extract_fragments_are_verbatim():
    s = _stmt("a", "We believe every child born in the united states of america is a citizen.", "A")
    sync = {"born in the united states", "child born in the united states of"}
    frags = extract._dry_fragments(s, sync, _TAX)
    assert frags, "expected at least one fragment"
    for f in frags:
        assert verify.is_verbatim(f["text"], s["text"]), f
        assert "immigration" in f["topics"]


def test_cluster_requires_three_distinct_members():
    frag = "born in the united states of america are citizens"
    ann = [{"text": frag, "topics": ["immigration"], "statement": f"sha256:{c}", "bioguide": c}
           for c in ("A", "B", "C")]
    tps = cluster.cluster_day("D", "2026-06-30", ann)
    assert len(tps) == 1 and tps[0]["member_count"] == 3

    two = ann[:2]
    assert cluster.cluster_day("D", "2026-06-30", two) == []


def test_cluster_collapses_joint_release_to_one_unit():
    """A joint/delegation release must count as 1 unit in the talking-point path, not N (§11 trap 2)."""
    frag = "we demand a full and independent investigation now"
    # all 3 signatories share one joint_group -> 1 unit -> below the >=3 floor -> not published
    joint = [{"text": frag, "topics": [], "statement": f"sha256:{c}", "bioguide": c, "joint_group": "joint:x"}
             for c in "ABC"]
    assert cluster.cluster_day("D", "2026-06-30", joint) == []
    # 2 independent members + a joint block (counts as 1) = 3 units -> published, member_count 3
    mixed = [{"text": frag, "topics": [], "statement": "sha256:A", "bioguide": "A", "joint_group": None},
             {"text": frag, "topics": [], "statement": "sha256:B", "bioguide": "B", "joint_group": None},
             {"text": frag, "topics": [], "statement": "sha256:C", "bioguide": "C", "joint_group": "joint:x"},
             {"text": frag, "topics": [], "statement": "sha256:D", "bioguide": "D", "joint_group": "joint:x"}]
    tps = cluster.cluster_day("D", "2026-06-30", mixed)
    assert len(tps) == 1 and tps[0]["member_count"] == 3
    assert len(tps[0]["fragments"]) == 3  # one receipt per unit, not per signatory


def test_iter_jsonl_skips_malformed_lines():
    """Skip-and-log: a truncated line in a mirror file must not crash the degraded-mode read."""
    import os
    import tempfile
    from pipeline import util
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    Path(path).write_text('{"a":1}\n{"a":2,"trunc\n{"a":3}\n', encoding="utf-8")
    try:
        rows = list(util.iter_jsonl(Path(path)))
        assert [r["a"] for r in rows] == [1, 3]
    finally:
        os.unlink(path)


def test_dry_daily_line_passes_verifier_and_uses_only_stats_numbers():
    tps = [{"id": "2026-06-30-D-00", "party": "D", "day": "2026-06-30", "label": "l",
            "member_count": 3, "statements": ["sha256:a", "sha256:b", "sha256:c"],
            "fragments": [{"text": "born in the united states of america", "statement": "sha256:a"}],
            "topics": ["immigration"]}]
    party_stmts = [_stmt("a", "x", "A"), _stmt("b", "y", "B"), _stmt("c", "z", "C")] * 6  # 18 -> not quiet
    top = {"text": "born in the united states of america", "members": 3, "first_sayer": "Rep A"}
    stmt_by_id = {s["id"]: s for s in party_stmts}
    dl = distill.daily_line("D", "2026-06-30", party_stmts, tps, top, stmt_by_id)
    assert dl["verifier"]["passed"] is True
    assert dl["fallback"] is False
    # every number in the composite is in the STATS block
    ok, off = verify.numbers_whitelisted(dl["composite"], str(dl["stats"]))
    assert ok, off


def test_two_lane_enforcement_lane2_excluded_from_ledger():
    """§5.1 machine enforcement: Lane 2 (Bluesky/floor) records are blocked from every
    comparative aggregator at the engine's eligibility gate — they cannot move a cross-party
    number. Also verified end-to-end below with enough Lane-1 volume to clear the DF-share cap."""
    from pipeline.phrases import PhraseEngine
    eng = PhraseEngine()
    assert eng._eligible({"lane": 1, "syndicated": False, "member": {"party": "D", "bioguide": "A"}}) == "D"
    assert eng._eligible({"lane": 2, "syndicated": False, "member": {"party": "D", "bioguide": "Z"}}) is None
    assert eng._eligible({"lane": None, "member": {"party": "R", "bioguide": "B"}}) is None

    # End-to-end: 3 Lane-1 members share a phrase amid filler; a Lane-2 member using the SAME
    # phrase must not appear in its member list. Filler keeps the phrase's DF-share under the cap.
    phrase = "we will protect the affordable care act for every family"
    stmts = [{"id": f"sha256:{c}", "text": f"Today {phrase}.", "published_at": "2026-06-30",
              "lane": 1, "syndicated": False, "congress": 119, "member": {"bioguide": c, "party": "D"}}
             for c in "ABC"]
    for i in range(80):  # filler so the phrase is a small share of the stratum
        stmts.append({"id": f"sha256:f{i}", "text": f"We support local project number {i} for our district roads.",
                      "published_at": "2026-06-30", "lane": 1, "syndicated": False, "congress": 119,
                      "member": {"bioguide": f"F{i}", "party": "D"}})
    stmts.append({"id": "sha256:Z", "text": f"Online: {phrase} now.", "published_at": "2026-06-30",
                  "lane": 2, "syndicated": False, "congress": 119, "member": {"bioguide": "Z", "party": "D"}})
    ledger = PhraseEngine().build(stmts)
    hit = next((k for k in ledger if "affordable care act" in k), None)
    assert hit, "expected the synchronized phrase in the ledger"
    day = ledger[hit]["daily"]["2026-06-30"]
    assert day["D"] == 3 and "Z" not in day.get("members_D", [])


def test_neutrality_hashes_are_single_valued_for_both_parties():
    # prompts_sha / thresholds_sha are computed once and applied to both parties by construction
    ps = ops.prompts_sha()
    assert set(ps) == {"P1", "P2", "P3"} and all(ps.values())
    assert ops.thresholds_sha() == ops.thresholds_sha()  # deterministic
