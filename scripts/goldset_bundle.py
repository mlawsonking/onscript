"""Render annotator packets from a sealed gold-set sample.

Writes, for each annotator, a self-contained HTML packet and a CSV answer sheet under
evaluation/goldset/bundles/<sample>/. Item order is randomized per annotator with a
recorded seed. No network, no API budget.

Usage:

    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_bundle.py pilot
    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_bundle.py full --annotators ann-a ann-b
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import config, goldset_bundle  # noqa: E402


GOLDSET_DIR = ROOT / "evaluation" / "goldset"
STATEMENTS_PATH = config.STATE / "statements.jsonl.gz"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", choices=["pilot", "full"])
    parser.add_argument("--annotators", nargs="+", default=["ann-a", "ann-b"])
    parser.add_argument("--seed", default=None,
                        help="Order seed; defaults to the sealed sample seed plus '-order'.")
    parser.add_argument("--format", choices=["app", "packet", "both"], default="both",
                        help="app: interactive click app; packet: read-only HTML + CSV; both.")
    args = parser.parse_args()

    sample = json.loads((GOLDSET_DIR / f"{args.sample}.sample.json").read_text(encoding="utf-8"))
    candidates = sample["candidates"]
    seed = args.seed or f"{sample['seed']}-order"

    print(f"loading statements from {STATEMENTS_PATH} ...", flush=True)
    by_id, by_day = goldset_bundle.load_statements(STATEMENTS_PATH)
    print(f"building {len(candidates)} items ...", flush=True)
    items_by_id = {
        candidate["candidate_id"]: goldset_bundle.build_item(candidate, by_id, by_day)
        for candidate in candidates
    }

    out_dir = GOLDSET_DIR / "bundles" / args.sample
    out_dir.mkdir(parents=True, exist_ok=True)
    written_paths = []
    for annotator in args.annotators:
        ordered = goldset_bundle.annotator_order(candidates, seed, annotator)
        items = [items_by_id[row["candidate_id"]] for row in ordered]
        written = []
        if args.format in ("app", "both"):
            app_page = goldset_bundle.render_app(
                items, annotator_id=annotator, sample=args.sample, seed=seed)
            path = out_dir / f"{annotator}.app.html"
            path.write_text(app_page, encoding="utf-8")
            written_paths.append(path)
            written.append("app.html")
        if args.format in ("packet", "both"):
            html_page = goldset_bundle.render_html(
                items, annotator_id=annotator, sample=args.sample, seed=seed)
            csv_sheet = goldset_bundle.render_csv(items)
            packet_path = out_dir / f"{annotator}.packet.html"
            sheet_path = out_dir / f"{annotator}.answersheet.csv"
            packet_path.write_text(html_page, encoding="utf-8")
            sheet_path.write_text(csv_sheet, encoding="utf-8")
            written_paths.extend([packet_path, sheet_path])
            written.append("packet.html + answersheet.csv")
        with_support = sum(1 for item in items if item["support"])
        print(f"  {annotator}: {len(items)} items, {with_support} with support set "
              f"-> {', '.join(written)}", flush=True)

    # docs/35 section 10.6 publishes the bundle, so it clears the publication privacy floor
    # here rather than at the moment someone uploads it.
    certificate = goldset_bundle.certify_publishable(written_paths)
    certificate["sample"] = args.sample
    certificate["seal_hash"] = sample["seal_hash"]
    (out_dir / "PUBLISH-CHECK.json").write_text(
        json.dumps(certificate, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    print(f"publish check: {certificate['files_scanned']} files scanned, "
          f"{certificate['admitted_forms_found']} admitted forms found, canary "
          f"{certificate['canary_version']}", flush=True)
    print(f"wrote {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
