"""Golden-set tone regression (§Session-8). A frozen set of representative STATS inputs, rendered
through the DETERMINISTIC composer, snapshotted so any prompt/composer change that alters the voice
fails a test and forces a conscious re-freeze (a decline into snark is a diff, not a vibe).

  python scripts/golden_render.py            # render + show register violations (eyeball the LLM too)
  python scripts/golden_render.py --freeze   # rewrite tests/golden/deterministic.json (intentional change)

The LLM voice is non-deterministic, so its regression is manual: on a prompt/model bump, render the
same fixtures live and eyeball them against the deterministic reference for register drift.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import distill  # noqa: E402

GOLDEN = Path(__file__).resolve().parents[1] / "tests" / "golden" / "deterministic.json"

# Representative STATS blocks (the shape build_stats emits), covering the voice's real branches.
FIXTURES = {
    "coordinated": {"party": "D", "day": "2026-07-13", "statements": 74, "sync_min": 3,
                    "talking_points": [
                        {"label": "21st century road to housing", "members": 10,
                         "quote": "the bipartisan 21st century road to housing act", "topics": ["housing"]},
                        {"label": "border security now", "members": 3,
                         "quote": "we support border security now", "topics": ["immigration"]}],
                    "top_phrase": {"text": "21st century road to housing", "members": 13}},
    "quiet_day": {"party": "R", "day": "2026-07-13", "statements": 8, "sync_min": 3,
                  "talking_points": [], "top_phrase": {"text": "border security now", "members": 4}},
    "no_coordination": {"party": "R", "day": "2026-07-13", "statements": 51, "sync_min": 3,
                        "talking_points": [], "top_phrase": None},
    "multi_cluster": {"party": "D", "day": "2026-07-13", "statements": 120, "sync_min": 3,
                      "talking_points": [
                          {"label": "protect medicare", "members": 8, "quote": "we will protect medicare", "topics": ["health"]},
                          {"label": "lower drug prices", "members": 6, "quote": "lower prescription drug prices", "topics": ["health"]},
                          {"label": "defend democracy", "members": 5, "quote": "defend our democracy", "topics": ["other"]}],
                      "top_phrase": {"text": "protect medicare", "members": 9}},
}


def render(stats: dict) -> str:
    quiet = stats["statements"] < 15
    return distill._quiet_dry(stats) if quiet else distill._compose_dry(stats)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()
    rendered = {name: render(s) for name, s in FIXTURES.items()}
    if args.freeze:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps({"fixtures": FIXTURES, "deterministic": rendered}, indent=1,
                                     ensure_ascii=False), encoding="utf-8")
        print(f"froze {len(rendered)} golden outputs -> {GOLDEN}")
        return 0
    for name, text in rendered.items():
        viol = distill.register_violations(text)
        print(f"--- {name} ---\n{text}\n  register: {'CLEAN' if not viol else viol}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
