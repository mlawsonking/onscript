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


def test_neutrality_hashes_are_single_valued_for_both_parties():
    # prompts_sha / thresholds_sha are computed once and applied to both parties by construction
    ps = ops.prompts_sha()
    assert set(ps) == {"P1", "P2", "P3"} and all(ps.values())
    assert ops.thresholds_sha() == ops.thresholds_sha()  # deterministic
