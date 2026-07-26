"""Run deterministic gold-set harness operations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import goldset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    metrics_parser = subparsers.add_parser("metrics")
    metrics_parser.add_argument("input", type=Path)
    sample_parser = subparsers.add_parser("sample")
    sample_parser.add_argument("input", type=Path)
    sample_parser.add_argument("--per-stratum", type=int, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if args.command == "metrics":
        result = goldset.run_synthetic(payload)
    else:
        result = goldset.sample_candidates(payload.get("candidates") or [], args.per_stratum)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
