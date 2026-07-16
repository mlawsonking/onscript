"""§1.4.1 acceptance gate as a CODE-OWNED number (Constitution: numbers come from code).

This test file exists because the gate was tracked in prose and the prose was wrong. On 2026-07-16
the canon read "the 3-consecutive gate is at 2/3 — the 07-16 cron completes it". That cron published
the apology stub for both parties. The false claim survived because `gh run list` reported `success`
for all three runs — an Actions success only means the workflow exited 0, which it does just as
happily when the Daily Line falls back.

All $0, no network; manifests are written to a temp dir, never to real derived data.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import ops  # noqa: E402


def _manifests(tmp: Path, rows):
    """rows: [(day, unattended, degraded)] or [(day, unattended, degraded, forced)]"""
    for r in rows:
        day, unattended, degraded = r[0], r[1], r[2]
        forced = r[3] if len(r) > 3 else False
        m = {"day": day, "unattended": unattended, "degraded": degraded,
             "forced_finalize": forced, "event": "schedule" if unattended else "workflow_dispatch"}
        (tmp / f"assemble-{day}.json").write_text(json.dumps(m), encoding="utf-8")
    return tmp


def test_three_clean_unattended_including_a_weekend_passes():
    with tempfile.TemporaryDirectory() as d:
        tmp = _manifests(Path(d), [("2026-07-17", True, False),   # Fri
                                   ("2026-07-18", True, False),   # Sat
                                   ("2026-07-19", True, False)])  # Sun
        r = ops.unattended_streak("2026-07-19", manifest_dir=tmp)
        assert r["value"] == 3 and r["weekend_day"] is True and r["passes"] is True


def test_three_clean_unattended_with_no_weekend_day_does_not_pass():
    """The gate says "(>=1 weekend day)" — a weekday-only streak is not the gate. Weekends are when
    the corpus goes quiet, which is exactly the condition worth proving unattended."""
    with tempfile.TemporaryDirectory() as d:
        tmp = _manifests(Path(d), [("2026-07-14", True, False),   # Tue
                                   ("2026-07-15", True, False),   # Wed
                                   ("2026-07-16", True, False)])  # Thu
        r = ops.unattended_streak("2026-07-16", manifest_dir=tmp)
        assert r["value"] == 3 and r["weekend_day"] is False and r["passes"] is False
        assert "weekend" in r["note"]


def test_the_real_2026_07_16_history_reads_zero_not_three():
    """THE REGRESSION THIS FILE EXISTS FOR. Two clean crons (07-14, 07-15) then a degraded one
    (07-16, the typography false-negative -> apology stub both parties). Actions reported success for
    all three. The gate is 0, because the streak is counted from the HEAD and the head fell back."""
    with tempfile.TemporaryDirectory() as d:
        tmp = _manifests(Path(d), [("2026-07-14", True, False),
                                   ("2026-07-15", True, False),
                                   ("2026-07-16", True, True)])   # degraded = the apology stub
        r = ops.unattended_streak("2026-07-16", manifest_dir=tmp)
        assert r["value"] == 0 and r["passes"] is False


def test_a_degraded_day_breaks_the_streak_it_does_not_shorten_it():
    with tempfile.TemporaryDirectory() as d:
        tmp = _manifests(Path(d), [("2026-07-17", True, False),
                                   ("2026-07-18", True, True),    # degraded Sat
                                   ("2026-07-19", True, False)])  # clean Sun
        r = ops.unattended_streak("2026-07-19", manifest_dir=tmp)
        assert r["value"] == 1 and r["passes"] is False           # only the Sunday survives


def test_a_forced_finalize_is_not_a_real_run():
    """forced_finalize means the readiness gate waited out MAX_WAIT and published a day upstream
    never filled. Honest, but not "a real run" for acceptance purposes."""
    with tempfile.TemporaryDirectory() as d:
        tmp = _manifests(Path(d), [("2026-07-17", True, False),
                                   ("2026-07-18", True, False),
                                   ("2026-07-19", True, False, True)])   # forced
        r = ops.unattended_streak("2026-07-19", manifest_dir=tmp)
        assert r["value"] == 0


def test_a_human_dispatch_at_the_head_does_not_count():
    """A repair-by-dispatch is exactly what happened on 07-16 and it must never be counted toward an
    UNATTENDED gate — that is the whole word."""
    with tempfile.TemporaryDirectory() as d:
        tmp = _manifests(Path(d), [("2026-07-17", True, False),
                                   ("2026-07-18", True, False),
                                   ("2026-07-19", False, False)])   # workflow_dispatch
        r = ops.unattended_streak("2026-07-19", manifest_dir=tmp)
        assert r["value"] == 0


def test_pre_instrumentation_manifests_fail_closed():
    """A manifest with no `unattended` field cannot PROVE it was a cron, so it is not counted.
    The streak legitimately reads 0 until instrumented runs accumulate — we do not backfill a claim
    we cannot support."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for day in ("2026-07-13", "2026-07-14", "2026-07-15"):
            (tmp / f"assemble-{day}.json").write_text(
                json.dumps({"day": day, "degraded": False}), encoding="utf-8")  # legacy shape
        r = ops.unattended_streak("2026-07-15", manifest_dir=tmp)
        assert r["value"] == 0 and r["passes"] is False


def test_manifest_records_who_triggered_the_run():
    """The field the gate rests on. Without it no code can tell a cron from a human dispatch, which
    is why this gate was hand-counted — and miscounted."""
    import inspect

    from pipeline import run_assemble
    src = inspect.getsource(run_assemble.assemble)
    assert '"event": os.environ.get("GITHUB_EVENT_NAME") or "local"' in src
    assert '"unattended": os.environ.get("GITHUB_EVENT_NAME") == "schedule"' in src


def test_a_skipped_day_breaks_the_streak_rather_than_being_hopped_over():
    """Manifests are keyed by TARGET day, and a NO-OP day (readiness gate: upstream had not filled,
    $0, nothing published) leaves NO manifest. Walking the manifest list without an adjacency check
    would hop that gap and read 07-13/07-15/07-16 as "three consecutive" — passing a launch gate on a
    machine that skipped a day. Caught while simulating tomorrow's cron against real state."""
    with tempfile.TemporaryDirectory() as d:
        tmp = _manifests(Path(d), [("2026-07-13", True, False),
                                   # 2026-07-14 NO-OP -> no manifest at all
                                   ("2026-07-15", True, False),
                                   ("2026-07-16", True, False)])
        r = ops.unattended_streak("2026-07-16", manifest_dir=tmp)
        assert r["value"] == 2, "the gap must stop the walk, not be skipped over"
        assert r["passes"] is False


def test_adjacency_holds_across_a_month_boundary():
    with tempfile.TemporaryDirectory() as d:
        tmp = _manifests(Path(d), [("2026-07-30", True, False),   # Thu
                                   ("2026-07-31", True, False),   # Fri
                                   ("2026-08-01", True, False)])  # Sat
        r = ops.unattended_streak("2026-08-01", manifest_dir=tmp)
        assert r["value"] == 3 and r["weekend_day"] is True and r["passes"] is True
