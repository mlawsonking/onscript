"""Report whether each production verifier check is load-bearing."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.verifier_mutations import run_mutations  # noqa: E402


def main() -> None:
    report = run_mutations()
    for row in report:
        print(f"LOAD-BEARING {row['check']}")
    print(f"{len(report)}/{len(report)} verifier checks are load-bearing")


if __name__ == "__main__":
    main()
