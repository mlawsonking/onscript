"""Intake returned answer sheets: validate, score agreement, build the review queue.

One of the two operator commands, in two modes.

Two-annotator mode (docs/35 sections 1 to 9) reads the two annotators' sheets, computes
per-task agreement with the pilot gates, and writes the adjudication queue.

Single-human-rater mode (docs/35 section 10) reads Michael's sheet and the model rater's
sheet, computes human-versus-model agreement labeled as exactly that, and writes the triage
queue for his second look. The pilot gates are not evaluated in this mode and every output
carries the mandatory provenance label.

Both modes are deterministic: no network, no API budget.

Usage:

    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_intake.py pilot \\
        --a evaluation/goldset/bundles/pilot/ann-a.answersheet.csv \\
        --b evaluation/goldset/bundles/pilot/ann-b.answersheet.csv

    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_intake.py pilot \\
        --human evaluation/goldset/bundles/pilot/michael.answersheet.csv \\
        --model evaluation/goldset/bundles/pilot/model-rater.answersheet.csv
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

from pipeline import config, goldset_bundle, goldset_metrics, goldset_single  # noqa: E402


GOLDSET_DIR = ROOT / "evaluation" / "goldset"
STATEMENTS_PATH = config.STATE / "statements.jsonl.gz"


def _load_answers(path: Path, annotator_id: str):
    rows = goldset_metrics.read_answer_csv(Path(path).read_text(encoding="utf-8"), annotator_id)
    errors = goldset_metrics.validate_rows(rows)
    return rows, errors


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")


def _blinded_context(candidates: list[dict], ids: set[str], out_path: Path, seed: str,
                     sample_name: str) -> None:
    print(f"rendering blinded context for {len(ids)} items ...", flush=True)
    by_id, by_day = goldset_bundle.load_statements(STATEMENTS_PATH)
    rows = [row for row in candidates if row["candidate_id"] in ids]
    items = [goldset_bundle.build_item(row, by_id, by_day) for row in rows]
    out_path.write_text(
        goldset_bundle.render_html(items, annotator_id="second-look", sample=sample_name,
                                   seed=seed),
        encoding="utf-8")


def run_single(args, sample: dict, candidates: list[dict]) -> int:
    """docs/35 section 10: one human rater, one model reader, triage instead of adjudication."""
    human_rows, human_errors = _load_answers(args.human, args.human_rater)
    model_rows, model_errors = _load_answers(args.model, args.model_rater)
    if human_errors or model_errors:
        print("SCHEMA VALIDATION FAILED", flush=True)
        for who, errors in (("human", human_errors), ("model", model_errors)):
            for error in errors[:50]:
                print(f"  [{who}] {error}", flush=True)
        return 1
    print(f"validated: human={len(human_rows)} rows, model={len(model_rows)} rows", flush=True)

    report = goldset_single.human_versus_model_report(
        human_rows, model_rows, candidates, human_rater=args.human_rater,
        model_rater=args.model_rater, sample=args.sample)
    queue = goldset_single.triage_queue(human_rows, model_rows, candidates)

    out_dir = GOLDSET_DIR / "intake" / args.sample / "single"
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "human-versus-model-agreement.json", report)
    (out_dir / "triage-queue.csv").write_text(
        goldset_single.render_triage_queue(queue), encoding="utf-8")
    (out_dir / "triage-template.csv").write_text(
        goldset_single.render_triage_template(queue), encoding="utf-8")

    disputed = goldset_single.triage_required_ids(queue)
    if disputed and not args.no_context:
        _blinded_context(candidates, disputed, out_dir / "triage-context.html",
                         sample["seed"], f"{args.sample}-triage")

    agreement = report["human_versus_model_agreement"]
    print(f"\nhuman versus model agreement (items rated by both: "
          f"{report['items_rated_by_both']})", flush=True)
    for task, entry in sorted(agreement.items()):
        print(f"  {task:26s} agreement={entry['observed_agreement']} "
              f"n={entry['items']} disagreed={entry['disagreed']}", flush=True)
    print("\nThis is not inter-annotator agreement. One human rated these items; the model is a "
          "second reading of the same guide, used for triage only.", flush=True)
    print(f"\npilot gates: not evaluated. {report['pilot_gates']['reason']}", flush=True)
    print(f"triage queue: {len(disputed)} disagreements for a second look "
          f"({report['triage']['by_reason']})", flush=True)
    print(f"label: {report['provenance']['label']}", flush=True)
    print(f"wrote {out_dir}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", choices=["pilot", "full"])
    parser.add_argument("--a", help="annotator A answer sheet CSV (two-annotator mode)")
    parser.add_argument("--b", help="annotator B answer sheet CSV (two-annotator mode)")
    parser.add_argument("--annotator-a", default="ann-a")
    parser.add_argument("--annotator-b", default="ann-b")
    parser.add_argument("--human", help="the single human rater's answer sheet (docs/35 s10)")
    parser.add_argument("--model", help="the model rater's answer sheet (docs/35 s10)")
    parser.add_argument("--human-rater", default="michael")
    parser.add_argument("--model-rater", default="model-rater")
    parser.add_argument("--no-context", action="store_true",
                        help="skip the blinded HTML (faster, no corpus load)")
    args = parser.parse_args()

    single = bool(args.human or args.model)
    dual = bool(args.a or args.b)
    if single and dual:
        parser.error("choose one mode: --a/--b (two annotators) or --human/--model (docs/35 s10)")
    if single and not (args.human and args.model):
        parser.error("single-rater mode needs both --human and --model")
    if not single and not (args.a and args.b):
        parser.error("two-annotator mode needs both --a and --b")

    sample = json.loads((GOLDSET_DIR / f"{args.sample}.sample.json").read_text(encoding="utf-8"))
    candidates = sample["candidates"]

    if single:
        return run_single(args, sample, candidates)

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
