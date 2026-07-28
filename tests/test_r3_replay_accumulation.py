"""R3: the gate fills incrementally, append-only, and a re-run is a no-op.

R-33.6 needs 60 complete days and production publishes one a day, so the only way the gate ever
fills is by re-running the same command for weeks. That makes the properties tested here the
load-bearing ones: a second run must not duplicate, must not rewrite, and must not re-spend.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

from pipeline import shadow_replay

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.replay_accumulate import accumulate  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
DAYS = ROOT / "data" / "derived" / "days"


def _live_rows(days=("2026-07-25",), parties=("D", "R")):
    """Evidence rows shaped exactly like a live run's, for testing the store itself."""
    rows = []
    for day in days:
        for party in parties:
            rows.append({
                "schema_version": 1, "method_version": shadow_replay.METHOD_VERSION,
                "mode": "live", "day": day, "party": party, "prompt_id": "P3",
                "replay_prompt_sha256": shadow_replay.replay_prompt_sha256(),
                "candidate_prompt": {"file": "P3_quiet_day.v1.2.txt", "version": "1.2",
                                     "sha256": "c" * 64},
                "request_sha256": f"{day}{party}".ljust(64, "a"),
                "response_sha256": "b" * 64, "response_text": "{}",
                "tokens_in": 10, "tokens_out": 5, "cost_usd": 0.0001,
                "record": {"composite": "x", "verifier_passed": True, "guards": {},
                           "fallback": False},
                "candidate": {"composite": "y", "verifier_passed": True, "guards": {},
                              "fallback": False},
                "changed": True,
            })
    return rows


def test_pending_is_the_eligible_party_days_with_no_evidence_yet():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        plan = shadow_replay.plan(DAYS)
        outstanding = shadow_replay.pending(DAYS, root)
        assert len(outstanding) == plan["ladder"]["gate_eligible_party_days"]
        shadow_replay.append_evidence(_live_rows(), root)
        assert shadow_replay.pending(DAYS, root) == outstanding, (
            "evidence under a different candidate prompt must not satisfy the current one")


def test_a_replayed_party_day_leaves_the_pending_set():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        outstanding = shadow_replay.pending(DAYS, root)
        assert outstanding
        day, party = outstanding[0]
        plan_row = next(row for row in shadow_replay.plan(DAYS)["party_day_plan"]
                        if (row["day"], row["party"]) == (day, party))
        rows = _live_rows(days=(day,), parties=(party,))
        rows[0]["candidate_prompt"] = plan_row["candidate_prompt"]
        shadow_replay.append_evidence(rows, root)
        assert (day, party) not in shadow_replay.pending(DAYS, root)


def test_a_second_run_appends_nothing_and_rewrites_nothing():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        first = shadow_replay.append_evidence(_live_rows(), root)
        assert first["appended"] == 2
        before = shadow_replay.evidence_path(root).read_bytes()
        second = shadow_replay.append_evidence(_live_rows(), root)
        assert second["appended"] == 0
        assert second["already_present"] == 2
        assert shadow_replay.evidence_path(root).read_bytes() == before, (
            "an idempotent re-run must not touch a single committed byte")


def test_appending_a_later_day_preserves_every_earlier_line_verbatim():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        shadow_replay.append_evidence(_live_rows(days=("2026-07-25",)), root)
        first_lines = shadow_replay.evidence_path(root).read_text(encoding="utf-8").splitlines()
        shadow_replay.append_evidence(_live_rows(days=("2026-07-26",)), root)
        after = shadow_replay.evidence_path(root).read_text(encoding="utf-8").splitlines()
        assert after[:len(first_lines)] == first_lines
        assert len(after) == len(first_lines) + 2


def test_a_new_candidate_prompt_replays_the_day_again_rather_than_reusing_it():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        shadow_replay.append_evidence(_live_rows(), root)
        moved = _live_rows()
        for row in moved:
            row["candidate_prompt"] = dict(row["candidate_prompt"], sha256="d" * 64)
        result = shadow_replay.append_evidence(moved, root)
        assert result["appended"] == 2, (
            "a different candidate prompt is a different instrument and needs its own evidence")


def test_evidence_rows_are_deterministic_given_the_responses():
    report = shadow_replay.run(DAYS)
    first = json.dumps(shadow_replay.evidence_rows(report), sort_keys=True)
    second = json.dumps(shadow_replay.evidence_rows(shadow_replay.run(DAYS)), sort_keys=True)
    assert first == second
    for token in ("generated_at", "updated_at", "timestamp"):
        assert token not in first


def test_gate_progress_is_measured_on_evidence_not_on_eligibility():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        status = accumulate(DAYS, root=root)
        assert status["gate_progress"]["party_days"]["observed"] == 0, (
            "an eligible day with no replayed candidate is a day the gate has not seen")
        assert status["eligible_gate_progress"]["party_days"]["observed"] == (
            status["ladder"]["gate_eligible_party_days"])
        assert status["pending_count"] == status["ladder"]["gate_eligible_party_days"]
        assert status["gate_progress"]["complete_days"]["required"] == 60
        assert status["gate_progress"]["passed"] is False


def test_the_dry_accumulator_writes_no_evidence_and_spends_nothing():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        status = accumulate(DAYS, root=root)
        assert status["mode"] == "dry_run"
        assert status["evidence"]["appended"] == 0
        assert shadow_replay.evidence_path(root).exists() is False


def test_the_accumulator_cli_is_rerunnable_and_reports_the_gate():
    with tempfile.TemporaryDirectory() as raw:
        command = [sys.executable, "scripts/replay_accumulate.py", "--days-dir", str(DAYS),
                   "--evidence-root", raw]
        first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        assert first.stdout == second.stdout, "the dry accumulator is not idempotent"
        status = json.loads(first.stdout)
        assert status["gate_progress"]["requirement"] == "R-33.6"
        assert status["pending_count"] == len(status["pending_party_days"])
