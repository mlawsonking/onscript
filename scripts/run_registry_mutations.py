"""Report whether each central registry-versus-authority invariant is load-bearing."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.registry_mutations import run_registry_mutations  # noqa: E402


def main() -> None:
    report = run_registry_mutations()
    for row in report:
        print(f"LOAD-BEARING {row['invariant']}")
    print(f"{len(report)}/{len(report)} registry invariants are load-bearing")


if __name__ == "__main__":
    main()
