"""Render the R-33.6 comparison report. Free, deterministic, and it never calls a model.

  scripts/replay_report.py --out data/derived/replay/comparison-report.md
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import config, replay_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-dir", type=Path, default=config.DERIVED / "days")
    parser.add_argument("--evidence-root", type=Path, default=None)
    parser.add_argument("--out", type=Path,
                        default=config.DERIVED / "replay" / "comparison-report.md")
    args = parser.parse_args()
    built = replay_report.build(args.days_dir, args.evidence_root)
    path = replay_report.write(built["report"], args.out, evidence_rows=built["evidence_rows"])
    print(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
