"""Compare live and candidate Daily Line prompts without spending by default."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import config, shadow_replay  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-dir", type=Path, default=config.DERIVED / "days")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--live", action="store_true", help="Enable real model calls.")
    parser.add_argument(
        "--allow-api-spend", action="store_true",
        help="Second required authorization for real model calls.",
    )
    args = parser.parse_args()
    report = shadow_replay.run(
        args.days_dir, live=args.live, allow_api_spend=args.allow_api_spend, limit=args.limit,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
