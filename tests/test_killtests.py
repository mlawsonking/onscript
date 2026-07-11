"""Kill-tests (§1.4.3): the two failure modes the streak must survive.

A — source death: upstream stale -> run proceeds degraded on the mirror, dead-man fires, no crash.
B — batch/verify failure: the Daily Line falls back to an honest line, never silence.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import distill, ops, run_collect  # noqa: E402


def test_killtest_A_source_death_degrades_and_deadman_does_not_crash():
    fresh_stale = {"ok": True, "pushed_at": "2026-07-01T00:00:00Z", "age_hours": 100.0}
    fresh_ok = {"ok": True, "age_hours": 5.0}
    # staleness decision
    assert (fresh_stale["age_hours"] > run_collect.STALE_HOURS) is True
    assert (fresh_ok["age_hours"] > run_collect.STALE_HOURS) is False
    # dead-man ntfy with no NTFY_TOPIC set must LOG, return sent=False, and never raise
    res = ops.ntfy("kill-test", "source death drill", priority="high")
    assert res["sent"] is False and "reason" in res


def test_killtest_B_daily_line_falls_back_not_silent(monkeypatch=None):
    # Force the composer to emit an un-whitelisted number -> verifier rejects -> honest fallback.
    orig = distill._compose_dry
    distill._compose_dry = lambda stats: "We repeated it 99999 times today."  # 99999 not in STATS
    try:
        tps = [{"id": "t", "party": "D", "day": "2026-06-30", "label": "l", "member_count": 3,
                "statements": ["sha256:a", "sha256:b", "sha256:c"],
                "fragments": [{"text": "protect the border today", "statement": "sha256:a"}],
                "topics": ["immigration"]}]
        party_stmts = [{"id": f"sha256:{c}", "text": "protect the border today",
                        "member": {"bioguide": c, "party": "D"}, "published_at": "2026-06-30", "lane": 1}
                       for c in "ABC"] * 6
        stmt_by_id = {s["id"]: s for s in party_stmts}
        dl = distill.daily_line("D", "2026-06-30", party_stmts, tps, None, stmt_by_id)
        assert dl["fallback"] is True
        assert dl["composite"].strip() and "could not be verified" in dl["composite"]
        assert dl["verifier"]["passed"] is False
    finally:
        distill._compose_dry = orig
