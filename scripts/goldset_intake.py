"""Intake returned answer sheets: validate, score agreement, build the adjudication queue.

One of the two operator commands. Reads a sealed sample and the two annotators' answer
sheets, validates both against the schema, computes per-task agreement (Cohen's kappa and
Krippendorff alpha) with the pilot gates, and writes the adjudication queue plus a blinded
context packet and a decisions template for every disagreement. No network, no API budget.

Usage:

    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_intake.py pilot \\
        --a evaluation/goldset/bundles/pilot/ann-a.answersheet.csv \\
        --b evaluation/goldset/bundles/pilot/ann-b.answersheet.csv
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

from pipeline import config, goldset_bundle, goldset_metrics  # noqa: E402


GOLDSET_DIR = ROOT / "evaluation" / "goldset"
STATEMENTS_PATH = config.STATE / "statements.jsonl.gz"


def _load_answers(path: Path, annotator_id: str):
    rows = goldset_metrics.read_answer_csv(Path(path).read_text(encoding="utf-8"), annotator_id)
    errors = goldset_metrics.validate_rows(rows)
    return rows, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", choices=["pilot", "full"])
    parser.add_argument("--a", required=True, help="annotator A answer sheet CSV")
    parser.add_argument("--b", required=True, help="annotator B answer sheet CSV")
    parser.add_argument("--annotator-a", default="ann-a")
    parser.add_argument("--annotator-b", default="ann-b")
    parser.add_argument("--no-context", action="store_true",
                        help="skip the blinded adjudication HTML (faster, no corpus load)")
    args = parser.parse_args()

    sample = json.loads((GOLDSET_DIR / f"{args.sample}.sample.json").read_text(encoding="utf-8"))
    candidates = sample["candidates"]

    rows_a, errors_a = _load_answers(args.a, args.annotator_a)
    rows_b, errors_b = _load_answers(args.b, args.annotator_b)
    if errors_a or errors_b:
        print("SCHEMA VALIDATION FAILED", flush=True)
        for who, errors in (("A", errors_a), ("B", errors_b)):
            for error in errors[:50]:
                print(f"  [{who}] {error}", flush=True)
        return 1
    print(f"validated: A={len(rows_a)} rows, B={len(rows_b)} rows", flush=True)

    report = goldset_metrics.agreement_report(rows_a, rows_b, candidates)
    queue = goldset_metrics.adjudication_queue(rows_a, rows_b, candidates)

    out_dir = GOLDSET_DIR / "intake" / args.sample
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "agreement.json").write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    # Adjudication queue CSV and a decisions template the adjudicator fills.
    queue_buffer = io.StringIO()
    writer = csv.writer(queue_buffer, lineterminator="\n")
    writer.writerow(["candidate_id", "reason", "a_gold_class", "b_gold_class",
                     "a_gold_family_id", "b_gold_family_id"])
    for row in queue:
        writer.writerow([row.get("candidate_id"), row.get("reason"), row.get("a_gold_class"),
                         row.get("b_gold_class"), row.get("a_gold_family_id"),
                         row.get("b_gold_family_id")])
    (out_dir / "adjudication-queue.csv").write_text(queue_buffer.getvalue(), encoding="utf-8")

    template = io.StringIO()
    writer = csv.writer(template, lineterminator="\n")
    writer.writerow(["candidate_id", "adjudicator_id", "gold_class", "gold_family_id"])
    for row in queue:
        if row.get("reason") in ("class", "family"):
            writer.writerow([row.get("candidate_id"), "", "", ""])
    (out_dir / "decisions-template.csv").write_text(template.getvalue(), encoding="utf-8")

    disputed_ids = {row["candidate_id"] for row in queue if row.get("reason") in ("class", "family")}
    if disputed_ids and not args.no_context:
        print(f"rendering blinded context for {len(disputed_ids)} disputed items ...", flush=True)
        by_id, by_day = goldset_bundle.load_statements(STATEMENTS_PATH)
        disputed = [c for c in candidates if c["candidate_id"] in disputed_ids]
        items = [goldset_bundle.build_item(c, by_id, by_day) for c in disputed]
        html_page = goldset_bundle.render_html(
            items, annotator_id="adjudicator", sample=f"{args.sample}-adjudication",
            seed=sample["seed"])
        (out_dir / "adjudication-context.html").write_text(html_page, encoding="utf-8")

    gates = report["pilot_gates"]
    print("\nagreement (dual-annotated items: "
          f"{report['dual_annotated_items']})", flush=True)
    for task, entry in report["tasks"].items():
        print(f"  {task:24s} kappa={entry['cohens_kappa']} "
              f"alpha={entry['krippendorff_alpha']} n={entry['items']}", flush=True)
    print("\npilot gates:", flush=True)
    for name, threshold in gates["thresholds"].items():
        value = gates["values"][name]
        status = "PASS" if gates["pass"][name] else "FAIL"
        print(f"  {name:34s} {value} >= {threshold}  {status}", flush=True)
    print(f"\nadjudication queue: {len(disputed_ids)} disagreements", flush=True)
    print(f"wrote {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
