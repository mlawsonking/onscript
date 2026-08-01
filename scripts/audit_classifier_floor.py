"""Audit the deterministic classifier against the phrases that actually published.

Evidence for docs/38. Runs the live classifier over every published talking-point claim and
every top-synchronized n-gram in the committed day artifacts, and reports the class
distribution, the fragment rate, and how convergence relates to class.

The sealed pilot sample is deliberately not read. Its shape distribution is a prior that would
contaminate an in-flight annotation pass (docs/35 section 10.2).

Deterministic. No network, no API budget. Changes nothing.

Usage:

    C:\\ProgramData\\miniconda3\\python.exe scripts\\audit_classifier_floor.py
    C:\\ProgramData\\miniconda3\\python.exe scripts\\audit_classifier_floor.py --json out.json
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import config, eligibility  # noqa: E402

DAYS = config.DERIVED / "days"

# A phrase ending on one of these needs a following word to complete its constituent. Only the
# tail is tested: a phrase that BEGINS with a preposition is usually a complete prepositional
# phrase ("on the house floor") and flagging those overcounts.
OPEN_TAIL = {
    "a", "an", "the", "of", "to", "for", "in", "on", "at", "by", "with", "from", "into",
    "and", "or", "but", "that", "this", "these", "those", "our", "their", "his", "her", "its",
    "is", "are", "was", "were", "be", "been", "has", "have", "had", "will", "would", "can",
    "could", "should", "as", "than", "who", "which", "when", "while", "any", "no", "not",
}


def dangling(phrase: str) -> bool:
    words = phrase.lower().split()
    return bool(words) and words[-1] in OPEN_TAIL


def classify(text: str, day: str) -> str:
    result = eligibility.classify_phrase(text, day=day)
    return result.get("surface_class") if isinstance(result, dict) else result


def collect() -> tuple[list[dict], list[dict]]:
    claims, sync = [], []
    for path in sorted(DAYS.glob("*.json")):
        day = path.stem
        payload = json.loads(path.read_text(encoding="utf-8"))
        talking = payload.get("talking_points") or {}
        if isinstance(talking, dict):
            for party in ("D", "R"):
                for row in (talking.get(party) or []):
                    text = (row.get("label") or "").strip()
                    if text:
                        claims.append({"day": day, "party": party, "phrase": text,
                                       "members": row.get("member_count") or 0,
                                       "surface_class": classify(text, day),
                                       "dangling": dangling(text)})
        for row in (payload.get("top_synchronized") or []):
            text = (row.get("ngram") or "").strip()
            if text:
                sync.append({"day": day, "party": row.get("party"), "phrase": text,
                             "n": row.get("n"), "peak": row.get("day_peak") or 0,
                             "surface_class": classify(text, day),
                             "dangling": dangling(text)})
    return claims, sync


def summarize(claims: list[dict], sync: list[dict]) -> dict:
    def distribution(rows):
        counts = Counter(r["surface_class"] for r in rows)
        return {cls: {"count": n, "share": round(n / len(rows), 4)}
                for cls, n in counts.most_common()} if rows else {}

    peaks = defaultdict(list)
    for row in sync:
        peaks[row["surface_class"]].append(row["peak"])
    broken = [r for r in claims if r["dangling"]]

    return {
        "schema_version": 1,
        "method_version": "classifier-floor-audit-v1",
        "population": {
            "day_artifacts": len(sorted(DAYS.glob("*.json"))),
            "published_claims": len(claims),
            "top_synchronized": len(sync),
            "member_mentions": sum(r["members"] for r in claims),
        },
        "published_claim_classes": distribution(claims),
        "top_synchronized_classes": distribution(sync),
        "convergence_by_class": {
            cls: {"count": len(vals), "mean_peak_members": round(sum(vals) / len(vals), 2)}
            for cls, vals in sorted(peaks.items(), key=lambda kv: -len(kv[1]))
        },
        "fragment_rate": {
            "numerator": len(broken),
            "denominator": len(claims),
            "estimate": round(len(broken) / len(claims), 4) if claims else None,
            "distinct_phrases": len(set(r["phrase"] for r in broken)),
            "member_mentions_reached": sum(r["members"] for r in broken),
            "estimator": "share of published claims whose last word requires a completion",
            "unit": "published talking-point claims",
            "window": "committed day artifacts under data/derived/days",
        },
        "most_shared_claims": sorted(claims, key=lambda r: -r["members"])[:12],
        "broken_claims": sorted(broken, key=lambda r: (r["day"], r["party"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None, help="write the full report to this path")
    args = parser.parse_args()

    claims, sync = collect()
    if not claims:
        print("no published claims found; is data/derived/days populated?", flush=True)
        return 1
    report = summarize(claims, sync)

    pop = report["population"]
    print(f"day artifacts {pop['day_artifacts']}, published claims {pop['published_claims']}, "
          f"top-synchronized {pop['top_synchronized']}", flush=True)

    print("\npublished claim classes:", flush=True)
    for cls, row in report["published_claim_classes"].items():
        print(f"  {cls:<14} {row['count']:>4} ({row['share']:>6.1%})", flush=True)

    print("\ntop-synchronized classes:", flush=True)
    for cls, row in report["top_synchronized_classes"].items():
        print(f"  {cls:<14} {row['count']:>4} ({row['share']:>6.1%})", flush=True)

    print("\nconvergence by class (mean members on a phrase):", flush=True)
    for cls, row in report["convergence_by_class"].items():
        print(f"  {cls:<14} n={row['count']:>4}  mean peak {row['mean_peak_members']:>5.1f}",
              flush=True)

    frag = report["fragment_rate"]
    print(f"\nfragment rate: {frag['numerator']}/{frag['denominator']} = {frag['estimate']:.1%} "
          f"({frag['distinct_phrases']} distinct, {frag['member_mentions_reached']} member "
          f"mentions)", flush=True)

    print("\nmost-shared published claims:", flush=True)
    for row in report["most_shared_claims"]:
        print(f"  {row['members']:>3} members  {row['surface_class']:<14} {row['phrase']!r}",
              flush=True)

    if args.json:
        Path(args.json).write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        print(f"\nwrote {args.json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
