"""Speaker-contamination audit sample (§Session-8). Press releases quote third parties — award
presenters, bill text, constituents. If extraction lifts a fragment from quoted words inside member
X's release, the ledger attributes it to X, and first-sayer/velocity inherit the error. This emits a
reproducible sample of displayed quotes with their source URL for Michael to hand-classify during the
dark-week audit (#77): open each URL, mark whether the quote is the member's OWN words or a third
party's. Contamination above ~2% => build deterministic quote-boundary detection before any
first-sayer/coordination claim ships.

  python scripts/audit/speaker_sample.py [--n 100]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline import config  # noqa: E402


def collect() -> list[dict]:
    rows = []
    ddir = config.DERIVED / "days"
    for p in sorted(ddir.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for party, tps in (d.get("talking_points") or {}).items():
            for tp in (tps or []):
                for c in (tp.get("citations") or []):
                    if c.get("quote") and c.get("url"):
                        rows.append({"day": d.get("day"), "party": party, "member": c.get("member"),
                                     "date": c.get("date"), "quote": c.get("quote"), "url": c.get("url")})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()
    rows = collect()
    if not rows:
        print("no cited quotes found — assemble more days (per-citation quotes exist from §Session-7 on).")
        return 0
    random.seed(1)  # reproducible
    sample = random.sample(rows, min(args.n, len(rows)))
    out = config.DERIVED / "audit" / "speaker_sample.tsv"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["idx\tday\tparty\tmember\tdate\tquote\turl\town_words_y_n"]
    for i, r in enumerate(sample, 1):
        lines.append("\t".join(str(x) for x in
                               (i, r["day"], r["party"], r["member"], r["date"], r["quote"], r["url"], "")))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(sample)} of {len(rows)} cited quotes -> {out}")
    print("Fill own_words_y_n: y = member's own words · n = quoted third party · ? = unclear.")
    print(">2% 'n' => build deterministic quote-boundary detection before any first-sayer claim ships.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
