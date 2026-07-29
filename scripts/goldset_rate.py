"""Run the model rater over a sealed gold-set bundle (docs/35 section 10.2).

The model is a second reading used for disagreement triage. It never writes a gold label.

Dry run is the default and costs nothing: it builds every frozen request, checks the live
rating instrument against the frozen registration, estimates the spend, and writes the
requests so they can be read before anyone pays for them. No Anthropic call is made and no
answer sheet is invented, because a fabricated sheet would look exactly like a real one.

The live run is Michael's act. It requires --allow-api-spend and ANTHROPIC_API_KEY, and it
refuses to start if the prompt or the annotation guide has drifted from the registration.

--transport session is the offline reader: a subscription session answers the same frozen
requests at no marginal cost, under the docs/03 precedent for one-time subscription-scripted
work. It runs in two steps, because the reader works between them. --emit writes the worksheet
the session reads; --collect validates the session's answers against the committed annotation
schema, writes the sheet, and seals it. Both steps refuse on instrument drift and spend
nothing.

Usage:

    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_rate.py pilot
    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_rate.py pilot --freeze
    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_rate.py pilot --allow-api-spend
    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_rate.py pilot ^
        --transport session --emit --reader-model claude-opus-5
    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_rate.py pilot ^
        --transport session --collect --reader-model claude-opus-5 --wall-seconds 4200
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import config, goldset_bundle, goldset_metrics, goldset_rater, util  # noqa: E402


GOLDSET_DIR = ROOT / "evaluation" / "goldset"
STATEMENTS_PATH = config.STATE / "statements.jsonl.gz"


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> tuple[list, list[str]]:
    """Every JSON object in a file, plus a named problem for every line that is not one."""
    rows: list = []
    problems: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            problems.append(f"line {number}: {error}")
    return rows, problems


def _freeze() -> int:
    registration = goldset_rater.registration()
    _write_json(goldset_rater.REGISTRATION_PATH, registration)
    print(f"froze the rating instrument: {registration['rating_prompt_sha256']}", flush=True)
    print(f"wrote {goldset_rater.REGISTRATION_PATH}", flush=True)
    return 0


def _session(args, requests, sample, out_dir: Path, frozen, estimate) -> int:
    """The offline reader: emit the worksheet, or collect and seal the answers it produced."""
    try:
        goldset_rater.assert_instrument_registered(frozen)
    except goldset_rater.RegistrationError as error:
        print(f"REFUSED: {error}", flush=True)
        return 1

    worksheet_path = out_dir / "model-rater.session-worksheet.jsonl"
    system_path = out_dir / "model-rater.session-system.txt"
    answers_path = out_dir / "model-rater.session-answers.jsonl"
    worksheet = goldset_rater.session_worksheet(requests)

    if args.emit:
        _write_jsonl(worksheet_path, worksheet)
        system_path.write_text(requests[0]["system"], encoding="utf-8")
        print(f"transport: session  reader: {args.reader_model}  "
              f"registered reader: {goldset_rater.MODEL}", flush=True)
        print(f"wrote {worksheet_path} ({len(worksheet)} groups) and "
              f"{system_path.name}", flush=True)
        print(f"answer sheet expected at {answers_path}", flush=True)
        print("session emit: $0 spent, no Anthropic call made, no answer sheet written.",
              flush=True)
        return 0

    if not answers_path.is_file():
        print(f"REFUSED: no session answers at {answers_path}. Run --emit, rate the "
              "worksheet, then --collect.", flush=True)
        return 1

    answers, malformed = _read_jsonl(answers_path)
    for problem in malformed:
        print(f"  malformed answer: {problem}", flush=True)

    # The worksheet the session read must be the worksheet these requests still produce. A
    # corpus or bundle that moved between emit and collect would silently repoint the answers.
    if worksheet_path.is_file():
        emitted, _ = _read_jsonl(worksheet_path)
        live = {cid: sha for group in worksheet
                for cid, sha in group["item_request_sha256"].items()}
        was = {cid: sha for group in emitted
               for cid, sha in (group.get("item_request_sha256") or {}).items()}
        if was and was != live:
            moved = sorted(cid for cid in set(was) | set(live) if was.get(cid) != live.get(cid))
            print(f"REFUSED: {len(moved)} item requests changed since --emit; the answers were "
                  f"given against different context. First: {moved[0]}", flush=True)
            return 1

    result = goldset_rater.run_session(requests, answers, reader_model=args.reader_model,
                                       wall_seconds=args.wall_seconds)
    if malformed:
        result["errors"] = [f"malformed answer line: {problem}" for problem in malformed] + \
            result["errors"]

    csv_text = goldset_rater.render_answer_csv(result["rows"])
    parsed = goldset_metrics.read_answer_csv(csv_text, result["rater_id"])
    row_problems = goldset_metrics.validate_rows(parsed)
    expected = sum(len(request["candidate_ids"]) for request in requests)

    sheet_path = out_dir / "model-rater.answersheet.csv"
    manifest_path = out_dir / "model-rater.run.json"
    complete = not result["errors"] and not row_problems and result["labels"] == expected
    if complete:
        sheet_path.write_text(csv_text, encoding="utf-8")

    manifest = {key: value for key, value in result.items() if key != "rows"}
    manifest["sample"] = args.sample
    manifest["seal_hash"] = sample["seal_hash"]
    manifest["items_expected"] = expected
    manifest["sheet_complete"] = complete
    manifest["sheet_rows"] = len(result["rows"])
    manifest["sheet_validation"] = row_problems
    manifest["sheet_sha256"] = util.sha256_hex(csv_text)
    manifest["sheet_file"] = f"evaluation/goldset/bundles/{args.sample}/{sheet_path.name}"
    manifest["api_equivalent_estimate"] = estimate
    _write_json(manifest_path, manifest)

    print(f"transport: session  reader: {args.reader_model}", flush=True)
    print(f"labels returned: {result['labels']} of {expected}", flush=True)
    for problem in (result["errors"] + row_problems)[:20]:
        print(f"  problem: {problem}", flush=True)
    print(f"sheet sha256: {manifest['sheet_sha256']}", flush=True)
    print("spend: $0.00 USD. No Anthropic call was made on this transport.", flush=True)
    if not complete:
        print(f"REFUSED to write {sheet_path.name}: the sheet is incomplete or invalid. "
              f"Wrote {manifest_path.name} naming every problem.", flush=True)
        return 1
    print(f"wrote {sheet_path} and {manifest_path.name}", flush=True)
    print("These labels are triage input only. They are never gold labels (docs/35 s10.2).",
          flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", choices=["pilot", "full"])
    parser.add_argument("--freeze", action="store_true",
                        help="write the frozen registration from the live prompt and stop")
    parser.add_argument("--allow-api-spend", action="store_true",
                        help="make the live calls; Michael's act, the only step that costs money")
    parser.add_argument("--model", default=goldset_rater.MODEL)
    parser.add_argument("--transport", choices=goldset_rater.TRANSPORTS, default="api",
                        help="api calls the model; session records a subscription session's "
                             "answers to the same frozen requests at no marginal cost")
    parser.add_argument("--emit", action="store_true",
                        help="session transport: write the worksheet the session reads")
    parser.add_argument("--collect", action="store_true",
                        help="session transport: validate the session's answers and seal the "
                             "sheet")
    parser.add_argument("--reader-model",
                        help="session transport: the model that actually read the items")
    parser.add_argument("--wall-seconds", type=float,
                        help="session transport: measured wall time of the rating pass")
    args = parser.parse_args()

    if args.freeze:
        return _freeze()

    if args.transport == "session":
        if args.emit == args.collect:
            parser.error("--transport session takes exactly one of --emit or --collect")
        if not args.reader_model:
            parser.error("--transport session needs --reader-model: the reader is recorded "
                         "truthfully, never as the registered API model")
        if args.allow_api_spend:
            parser.error("--transport session never spends; drop --allow-api-spend")
    elif args.emit or args.collect or args.reader_model or args.wall_seconds is not None:
        parser.error("--emit, --collect, --reader-model, and --wall-seconds belong to "
                     "--transport session")

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
        "instrument_drift": (goldset_rater.instrument_drift(frozen) if frozen else drift),
        "transport": args.transport,
        "estimate": estimate,
        "rater_id": (goldset_rater.session_rater_id(args.reader_model)
                     if args.transport == "session" else goldset_rater.rater_id()),
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

    if args.transport == "session":
        return _session(args, requests, sample, out_dir, frozen, estimate)

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
