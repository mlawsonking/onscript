"""Reproduce a deterministic committed subset without writing repository files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import goldset, surges  # noqa: E402


def _load(name: str) -> dict:
    return json.loads((ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"))


def _run() -> bytes:
    payload = {
        "surges": surges.build_rankings(_load("w8_rankings.json")),
        "goldset": goldset.run_synthetic(_load("w10_synthetic_annotations.json"))["metrics"],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> int:
    first, second = _run(), _run()
    first_hash = hashlib.sha256(first).hexdigest()
    second_hash = hashlib.sha256(second).hexdigest()
    result = {"first_sha256": first_hash, "second_sha256": second_hash,
              "byte_identical": first == second}
    print(json.dumps(result, sort_keys=True))
    return 0 if first == second else 1


if __name__ == "__main__":
    raise SystemExit(main())
