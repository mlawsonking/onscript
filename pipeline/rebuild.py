"""rebuild.py — reproduce derived JSON from the raw mirror alone, and prove determinism.

Acceptance §1.4.8: "rebuild.py reproduces one full day's derived JSON from raw alone."
Every derived layer is a pure function of the raw archive (design tenet 3), so rebuilding
twice must yield byte-identical output. This script runs the deterministic core over the
mirror twice and asserts the derived tree hashes match.

  python pipeline/rebuild.py            # rebuild from mirror + determinism check
  python pipeline/rebuild.py --once     # single rebuild (no double-run check)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import config, deterministic, fetch, util  # noqa: E402


def _derived_tree_hash() -> str:
    h = hashlib.sha256()
    for p in sorted(config.DERIVED.rglob("*.json")):
        if p.name.startswith("latest") or "manifest" in p.parts:
            continue  # manifests carry timestamps/run_ids; exclude from the determinism hash
        h.update(p.relative_to(config.DERIVED).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    records = fetch.load_mirror()
    if not records:
        print("no raw mirror found — run scripts/backfill_stage1.py first")
        return 2
    print(f"[rebuild] {len(records)} mirrored records")
    # One rebuild invocation is one measured run. Freeze its real start time across both passes so
    # generated_at keeps its meaning while time sampling cannot make otherwise identical JSON differ.
    generated_at = util.now_utc_iso()

    deterministic.run(records, run_id="rebuild-A", generated_at=generated_at)
    h1 = _derived_tree_hash()
    print(f"[rebuild] derived tree hash A: {h1}")
    if args.once:
        return 0

    deterministic.run(records, run_id="rebuild-B", generated_at=generated_at)
    h2 = _derived_tree_hash()
    print(f"[rebuild] derived tree hash B: {h2}")
    if h1 == h2:
        print("REPRODUCIBLE: derived JSON is byte-identical across rebuilds (§1.4.8) ✓")
        return 0
    print("NOT REPRODUCIBLE: derived output differs across rebuilds ✗")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
