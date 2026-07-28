"""Replay only the party-days that are not yet in the replay evidence file.

The R-33.6 gate needs 60 complete days and 200 party-days, and production publishes one day at
a time. So the gate fills by re-running this command, not by one big replay: each run finds the
gate-eligible party-days with no evidence yet under the current candidate prompt, replays only
those, and appends them. Existing lines are never rewritten, so the evidence file is a growing
record rather than a snapshot that has to be trusted.

Dry by default and free. It reports what is pending and what the gate stands at, and writes
nothing. Only --live --allow-api-spend replays, and only real model responses are ever appended.

  scripts/replay_accumulate.py                            what is pending, and gate progress
  scripts/replay_accumulate.py --live --allow-api-spend   replay the pending party-days
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import config, shadow_replay, util  # noqa: E402


def accumulate(days_dir: Path, *, root: Path | None = None, live: bool = False,
               allow_api_spend: bool = False, day: str | None = None, call=None) -> dict:
    """Find pending party-days, optionally replay them, and report the gate either way."""
    plan = shadow_replay.plan(days_dir)
    already = shadow_replay.load_evidence(root)
    outstanding = shadow_replay.pending(days_dir, root)

    appended = {"path": str(shadow_replay.evidence_path(root)), "appended": 0,
                "already_present": 0, "total_rows": len(already)}
    report = None
    if live and outstanding:
        report = shadow_replay.run(days_dir, live=True, allow_api_spend=allow_api_spend,
                                   only=set(outstanding), day=day, call=call)
        appended = shadow_replay.append_evidence(shadow_replay.evidence_rows(report), root)

    evidence = shadow_replay.load_evidence(root)
    covered_days = {row["day"] for row in evidence}
    return {
        "schema_version": 1,
        "method_version": shadow_replay.METHOD_VERSION,
        "mode": "live" if live else "dry_run",
        "evidence": appended,
        "replay_prompt_sha256": shadow_replay.replay_prompt_sha256(),
        "pending_party_days": [{"day": day_, "party": party} for day_, party in outstanding],
        "pending_count": len(outstanding),
        "evidence_party_days": len(evidence),
        "evidence_days": len(covered_days),
        "ladder": plan["ladder"],
        # Gate progress is measured on the EVIDENCE, not on what is eligible: an eligible day
        # with no replayed candidate is a day the gate has not actually seen.
        "gate_progress": shadow_replay.gate_progress(len(covered_days), len(evidence)),
        "eligible_gate_progress": plan["gate_progress"],
        "run": report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-dir", type=Path, default=config.DERIVED / "days")
    parser.add_argument("--evidence-root", type=Path, default=None)
    parser.add_argument("--live", action="store_true", help="Enable real model calls.")
    parser.add_argument("--allow-api-spend", action="store_true",
                        help="Second required authorization for real model calls.")
    parser.add_argument("--out", type=Path, help="Write the status report here as well.")
    args = parser.parse_args()

    try:
        report = accumulate(args.days_dir, root=args.evidence_root, live=args.live,
                            allow_api_spend=args.allow_api_spend)
    except shadow_replay.BudgetPreflightError as error:
        plan = shadow_replay.plan(args.days_dir)
        refusal = {
            "mode": "refused",
            "method_version": shadow_replay.METHOD_VERSION,
            "reason": str(error),
            "budget_preflight": shadow_replay.budget_preflight(
                plan["cost_projection"]["estimated_cost_usd"],
                bound_usd=shadow_replay.SPEND_BOUND_USD,
                day=datetime.now(timezone.utc).date().isoformat(),
            ),
            "pending_count": len(shadow_replay.pending(args.days_dir, args.evidence_root)),
            "gate_progress": plan["gate_progress"],
            "spend_usd": 0.0,
        }
        if args.out:
            util.write_json(args.out, refusal)
        print(json.dumps(refusal, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 2

    if args.out:
        util.write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
