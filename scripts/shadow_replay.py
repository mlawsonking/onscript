"""Compare the committed P2 v1.3 / P3 v1.1 record against a generated v1.4 / v1.2 candidate.

Dry by default and free. The live side is never generated: it is read from the committed
production record, so only the candidate side can ever cost money, and only behind both
--live and --allow-api-spend.

  scripts/shadow_replay.py --plan                      the free run plan and gate progress
  scripts/shadow_replay.py                             the dry comparison
  scripts/shadow_replay.py --freeze                    freeze the replay prompt registration
  scripts/shadow_replay.py --live --allow-api-spend    the live candidate replay
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-dir", type=Path, default=config.DERIVED / "days")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--plan", action="store_true",
                        help="Emit the run plan and gate progress. Never calls a model.")
    parser.add_argument("--freeze", action="store_true",
                        help="Write the replay prompt registration a live run is checked against.")
    parser.add_argument("--live", action="store_true", help="Enable real model calls.")
    parser.add_argument(
        "--allow-api-spend", action="store_true",
        help="Second required authorization for real model calls.",
    )
    parser.add_argument("--out", type=Path, help="Write the report or plan here as well.")
    args = parser.parse_args()

    if args.freeze:
        registration = shadow_replay.registration()
        util.write_json(shadow_replay.REGISTRATION_PATH, registration)
        print(json.dumps(registration, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")))
        return 0

    if args.plan:
        report = shadow_replay.plan(args.days_dir)
    else:
        try:
            report = shadow_replay.run(
                args.days_dir, live=args.live, allow_api_spend=args.allow_api_spend,
                limit=args.limit,
            )
        except shadow_replay.BudgetPreflightError as error:
            # An expected, well-understood refusal deserves a readable report, not a traceback:
            # the operator needs to see WHICH condition blocked and what the ledger said.
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
