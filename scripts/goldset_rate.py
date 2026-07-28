"""Run the model rater over a sealed gold-set bundle (docs/35 section 10.2).

The model is a second reading used for disagreement triage. It never writes a gold label.

Dry run is the default and costs nothing: it builds every frozen request, checks the live
rating instrument against the frozen registration, estimates the spend, and writes the
requests so they can be read before anyone pays for them. No Anthropic call is made and no
answer sheet is invented, because a fabricated sheet would look exactly like a real one.

The live run is Michael's act. It requires --allow-api-spend and ANTHROPIC_API_KEY, and it
refuses to start if the prompt or the annotation guide has drifted from the registration.

Usage:

    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_rate.py pilot
    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_rate.py pilot --freeze
    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_rate.py pilot --allow-api-spend
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import config, goldset_bundle, goldset_rater  # noqa: E402


GOLDSET_DIR = ROOT / "evaluation" / "goldset"
STATEMENTS_PATH = config.STATE / "statements.jsonl.gz"


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")


def _freeze() -> int:
    registration = goldset_rater.registration()
    _write_json(goldset_rater.REGISTRATION_PATH, registration)
    print(f"froze the rating instrument: {registration['rating_prompt_sha256']}", flush=True)
    print(f"wrote {goldset_rater.REGISTRATION_PATH}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", choices=["pilot", "full"])
    parser.add_argument("--freeze", action="store_true",
                        help="write the frozen registration from the live prompt and stop")
    parser.add_argument("--allow-api-spend", action="store_true",
                        help="make the live calls; Michael's act, the only step that costs money")
    parser.add_argument("--model", default=goldset_rater.MODEL)
    args = parser.parse_args()

    if args.freeze:
        return _freeze()

    sample = json.loads((GOLDSET_DIR / f"{args.sample}.sample.json").read_text(encoding="utf-8"))
    candidates = sample["candidates"]
    out_dir = GOLDSET_DIR / "bundles" / args.sample
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"loading statements from {STATEMENTS_PATH} ...", flush=True)
    by_id, by_day = goldset_bundle.load_statements(STATEMENTS_PATH)
    items_by_id = {
        candidate["candidate_id"]: goldset_bundle.build_item(candidate, by_id, by_day)
        for candidate in candidates
    }
    requests = goldset_rater.build_requests(candidates, items_by_id)
    estimate = goldset_rater.estimate_run(requests, model=args.model)

    live_registration = goldset_rater.registration()
    try:
        frozen = goldset_rater.load_registration()
        drift = goldset_rater.registration_drift(frozen)
    except goldset_rater.RegistrationError as error:
        frozen, drift = None, [str(error)]

    plan = {
        "sample": args.sample,
        "seal_hash": sample["seal_hash"],
        "registration": live_registration,
        "registration_frozen": bool(frozen) and not drift,
        "registration_drift": drift,
        "estimate": estimate,
        "rater_id": goldset_rater.rater_id(),
    }
    _write_json(out_dir / "model-rater.plan.json", plan)
    with (out_dir / "model-rater.requests.jsonl").open("w", encoding="utf-8") as handle:
        for request in requests:
            handle.write(json.dumps(request, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"requests: {estimate['requests']} over {estimate['items']} items "
          f"({args.sample}, seal {sample['seal_hash'][:16]})", flush=True)
    print(f"rating instrument: {live_registration['rating_prompt_sha256']}", flush=True)
    print(f"model: {args.model}  approx tokens in: {estimate['approx_tokens_in']}  "
          f"estimated cost: ${estimate['estimated_cost_usd']} (upper bound)", flush=True)
    print(f"wrote {out_dir / 'model-rater.plan.json'} and model-rater.requests.jsonl", flush=True)

    if not args.allow_api_spend:
        if drift:
            print(f"\nregistration: NOT frozen or drifted ({', '.join(drift)}). "
                  "Run with --freeze before a live run.", flush=True)
        else:
            print("\nregistration: frozen and matching.", flush=True)
        print("dry run: $0 spent, no Anthropic call made, no answer sheet written.", flush=True)
        print("A live run is Michael's act: rerun with --allow-api-spend.", flush=True)
        return 0

    # --- live path: Michael's act ------------------------------------------------
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("REFUSED: --allow-api-spend was given but ANTHROPIC_API_KEY is not set.",
              flush=True)
        return 1
    try:
        goldset_rater.assert_registered(frozen)
    except goldset_rater.RegistrationError as error:
        print(f"REFUSED: {error}", flush=True)
        return 1

    print(f"live run: {estimate['requests']} calls to {args.model} ...", flush=True)
    result = goldset_rater.run_live(requests, model=args.model)
    sheet_path = out_dir / "model-rater.answersheet.csv"
    sheet_path.write_text(goldset_rater.render_answer_csv(result["rows"]), encoding="utf-8")
    run_record = {key: value for key, value in result.items() if key != "rows"}
    run_record["sample"] = args.sample
    run_record["seal_hash"] = sample["seal_hash"]
    _write_json(out_dir / "model-rater.run.json", run_record)

    print(f"labels returned: {result['labels']} of {estimate['items']}", flush=True)
    for problem in result["errors"][:20]:
        print(f"  problem: {problem}", flush=True)
    print(f"tokens in {result['tokens_in']} out {result['tokens_out']}  "
          f"billed cost: ${result['cost_usd']}", flush=True)
    print(f"wrote {sheet_path}", flush=True)
    print("These labels are triage input only. They are never gold labels (docs/35 s10.2).",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
