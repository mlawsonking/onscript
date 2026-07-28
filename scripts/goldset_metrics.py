"""Compute the gold-set metric set with confidence intervals from adjudicated labels.

The second operator command. Merges the two annotators with the adjudicator decisions and
reports message precision, document-family pairwise precision and recall, the party error
gap, and the full confusion matrix, each with numerator, denominator, and 95% Wilson
interval. Refuses to report if any item is unresolved. No network, no API budget.

Usage:

    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_metrics.py pilot \\
        --a evaluation/goldset/bundles/pilot/ann-a.answersheet.csv \\
        --b evaluation/goldset/bundles/pilot/ann-b.answersheet.csv \\
        --decisions evaluation/goldset/intake/pilot/decisions.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import goldset_metrics  # noqa: E402


GOLDSET_DIR = ROOT / "evaluation" / "goldset"


def _read_decisions(path: Path | None) -> list[dict]:
    if not path:
        return []
    decisions = []
    reader = csv.DictReader(io.StringIO(Path(path).read_text(encoding="utf-8")))
    for row in reader:
        cid = (row.get("candidate_id") or "").strip()
        if not cid:
            continue
        decisions.append({
            "candidate_id": cid,
            "adjudicator_id": (row.get("adjudicator_id") or "").strip() or None,
            "gold_class": (row.get("gold_class") or "").strip(),
            "gold_family_id": (row.get("gold_family_id") or "").strip(),
        })
    return decisions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", choices=["pilot", "full"])
    parser.add_argument("--a", required=True)
    parser.add_argument("--b", required=True)
    parser.add_argument("--decisions", default=None)
    parser.add_argument("--annotator-a", default="ann-a")
    parser.add_argument("--annotator-b", default="ann-b")
    parser.add_argument("--split", default=None,
                        help="restrict metrics to one split: train, validation, or test")
    args = parser.parse_args()

    sample = json.loads((GOLDSET_DIR / f"{args.sample}.sample.json").read_text(encoding="utf-8"))
    candidates = sample["candidates"]
    if args.split:
        candidates = [row for row in candidates if row.get("split") == args.split]

    rows_a = goldset_metrics.read_answer_csv(Path(args.a).read_text(encoding="utf-8"), args.annotator_a)
    rows_b = goldset_metrics.read_answer_csv(Path(args.b).read_text(encoding="utf-8"), args.annotator_b)
    errors = goldset_metrics.validate_rows(rows_a) + goldset_metrics.validate_rows(rows_b)
    if errors:
        print("SCHEMA VALIDATION FAILED", flush=True)
        for error in errors[:50]:
            print(f"  {error}", flush=True)
        return 1

    decisions = _read_decisions(Path(args.decisions) if args.decisions else None)
    merged = goldset_metrics.merge_records(candidates, rows_a, rows_b, decisions)
    if merged["unresolved"]:
        print(f"UNRESOLVED: {len(merged['unresolved'])} items lack agreement or a decision.",
              flush=True)
        for row in merged["unresolved"][:20]:
            print(f"  {row['candidate_id']}: {row['reason']}", flush=True)
        print("Provide adjudicator decisions with --decisions and rerun.", flush=True)
        return 1

    metrics = goldset_metrics.metrics_with_intervals(merged["records"])
    out_dir = GOLDSET_DIR / "metrics" / args.sample
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"metrics{'-' + args.split if args.split else ''}.json"
    (out_dir / name).write_text(
        json.dumps(metrics, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    message = metrics["message_precision"]
    pairwise = metrics["family_pairwise"]
    gap = metrics["party_error_gap"]
    print(f"records: {metrics['records']}"
          + (f" (split={args.split})" if args.split else ""), flush=True)
    print(f"message precision: {message['estimate']} "
          f"({message['numerator']}/{message['denominator']}) ci95={message['ci95']}", flush=True)
    print(f"family pairwise precision: {pairwise['precision']['estimate']} "
          f"({pairwise['precision']['numerator']}/{pairwise['precision']['denominator']}) "
          f"ci95={pairwise['precision']['ci95']}", flush=True)
    print(f"family pairwise recall: {pairwise['recall']['estimate']} "
          f"({pairwise['recall']['numerator']}/{pairwise['recall']['denominator']}) "
          f"ci95={pairwise['recall']['ci95']}", flush=True)
    print(f"party error gap: {gap['absolute_gap']} ci95={gap['gap_ci95']} "
          f"(D {gap['D']['estimate']} n={gap['D']['denominator']}, "
          f"R {gap['R']['estimate']} n={gap['R']['denominator']})", flush=True)
    print(f"wrote {out_dir / name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
