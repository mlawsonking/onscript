"""The R-33.6 comparison report, in the shape a reader can check rather than trust.

Every measured number here carries its estimator, unit, window, denominator, and a rerunnable
command, because a prompt-activation decision is exactly the kind of claim that gets quoted
later without its denominator attached.

The report makes no flip recommendation and never will. R-33.6 names the conditions; the gate
decides. Prose that reads as a recommendation while the sample sits at a fraction of the
minimum is how a gate gets talked around, so this module states the fractions and stops.

Source precedence is explicit on the face of the report: if live evidence exists it is the
comparison, and the dry run is only ever labelled as what it is, a determinism check on the
harness that says nothing about the candidate prompt.
"""
from __future__ import annotations

from pathlib import Path

from . import config, shadow_replay


METHOD_VERSION = "replay-report-v1"

CHECKS = (
    ("verifier", "Full verifier pass",
     "party-days whose composite passes verify_daily_line", "party-day"),
    ("unit_mixing", "Unit mixing",
     "party-days where a sentence states one unit's count without labelling all three",
     "party-day"),
    ("quote_extension", "Quote extension",
     "party-days rendering a quote that is not a selected claim's display_quote", "party-day"),
    ("topic_label_assertion", "Topic-label assertion",
     "party-days asserting a classifier topic label outside quotation marks", "party-day"),
    ("multi_claim_sentence", "Multi-claim sentence",
     "party-days with a sentence mapping to more than one claim id", "party-day"),
    ("sentence_mapping_mismatch", "Sentence mapping mismatch",
     "party-days whose supplied sentence_claims differ from the computed mapping", "party-day"),
)

REPRODUCE = (
    r"C:\ProgramData\miniconda3\python.exe scripts\shadow_replay.py --plan",
    r"C:\ProgramData\miniconda3\python.exe scripts\shadow_replay.py",
    r"C:\ProgramData\miniconda3\python.exe scripts\replay_accumulate.py",
)


def quality_score(side: dict) -> int:
    """A stated ranking, so strongest and weakest are not a matter of taste.

    One point for the verifier, one for each clean zero-tolerance guard, one for not falling
    back. Higher is better; the maximum is 7.
    """
    guards = side.get("guards") or {}
    score = 1 if side.get("verifier_passed") else 0
    score += sum(1 for name in shadow_replay.GUARD_NAMES if not guards.get(name))
    score += 0 if side.get("fallback") else 1
    return score


def _rank(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: (-quality_score(row["candidate"]),
                                         quality_score(row["live"]),
                                         row["day"], row["party"]))


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    out.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return out


def _side_by_side(row: dict, label: str) -> list[str]:
    lines = [f"### {label}: {row['day']} {row['party']} ({row['prompt_id']})", ""]
    lines.extend(_table(
        ["", "Live (committed record)", "Candidate (generated)"],
        [
            ["Quality score (max 7)", quality_score(row["live"]), quality_score(row["candidate"])],
            ["Verifier", "pass" if row["live"]["verifier_passed"] else "fail",
             "pass" if row["candidate"]["verifier_passed"] else "fail"],
            ["Fallback", row["live"]["fallback"], row["candidate"]["fallback"]],
            ["Guard violations",
             ", ".join(name for name in shadow_replay.GUARD_NAMES
                       if row["live"]["guards"].get(name)) or "none",
             ", ".join(name for name in shadow_replay.GUARD_NAMES
                       if row["candidate"]["guards"].get(name)) or "none"],
            ["Generator", row["live"].get("generator") or "", row["candidate"].get("source") or ""],
        ]))
    lines += ["", "Live composite:", "", "> " + (row["live"]["composite"] or "(empty)"), "",
              "Candidate composite:", "", "> " + (row["candidate"]["composite"] or "(empty)"), ""]
    return lines


def render(report: dict, *, evidence_rows: list[dict] | None = None) -> str:
    """The full comparison report as markdown. Deterministic: no clock, no random ordering."""
    rows = report["party_day_results"]
    progress = report["gate_progress"]
    ladder = report["ladder"]
    live_mode = report["mode"] == "live"
    window = report["window"]
    window_label = (f"{window['start']} through {window['end']}" if window.get("start")
                    else "no scored party-day")
    denominator = report["candidate"]["offered_party_days"]

    lines = [
        "# R-33.6 shadow replay: P2 v1.4 and P3 v1.2 against the published record",
        "",
        f"Method version {report['method_version']}, report {METHOD_VERSION}. Replay instrument "
        f"`{report['replay_prompt_sha256'][:16]}`.",
        "",
        "## What this compares",
        "",
        "The live side is not generated. P2 v1.3 and P3 v1.1 ran in production on real days and "
        "their composites are committed in `data/derived/days`, so the live side of every "
        "party-day is what OnScript actually published, read back and rescored. Only the "
        "v1.4 and v1.2 side is generated. That is why the cost projection prices one call per "
        "party-day rather than two.",
        "",
        f"Mode: **{report['mode']}**. "
        + ("These are real model responses." if live_mode else
           "A dry run is a determinism check on the harness. It says nothing about the candidate "
           "prompt, because the composite it scores comes from the deterministic voice, not from "
           "v1.4 or v1.2. No dry row is admitted to the evidence file."),
        "",
        "## Gate progress",
        "",
    ]
    lines += _table(
        ["Minimum", "Observed", "Required", "Fraction", "Remaining"],
        [["Complete days", progress["complete_days"]["observed"],
          progress["complete_days"]["required"], progress["complete_days"]["fraction"],
          progress["complete_days"]["remaining"]],
         ["Party-days", progress["party_days"]["observed"], progress["party_days"]["required"],
          progress["party_days"]["fraction"], progress["party_days"]["remaining"]]])
    lines += [
        "",
        f"Estimator: {progress['estimator']}. Unit: {progress['unit']}. Window: {window_label}. "
        f"Denominator: {progress['denominator']}.",
        "",
        f"Minimum sample passed: **{report['activation_gate']['minimum_sample_passed']}**.",
        "",
        "## Why the population is smaller than the file count",
        "",
        "A committed day file is not automatically evidence about the live prompt. It counts "
        "only if its record was written BY the live prompt of its pair: the same prompt sha, a "
        "real model generator rather than the dry-run or deterministic voice, and a stats block "
        "of the schema the candidate prompt consumes. Mixing lineages in one comparison is what "
        "docs/37 rule 13 forbids.",
        "",
    ]
    lines += _table(
        ["Stage", "Count"],
        [["Committed day files", ladder["committed_day_files"]],
         ["Days carrying a composite for both parties", ladder["days_with_both_composites"]],
         ["Party-days carrying a composite", ladder["party_days_with_composites"]],
         ["Gate-eligible days", ladder["gate_eligible_days"]],
         ["Gate-eligible party-days", ladder["gate_eligible_party_days"]]])
    lines += ["", "Exclusions, counted over "
              f"{ladder['party_days_with_composites']} party-days (a party-day can fail more "
              "than one condition):", ""]
    lines += _table(["Reason", "Party-days"],
                    [[reason, count] for reason, count in ladder["exclusion_reasons"].items()])

    lines += ["", "## Per-check results", "",
              f"Window: {window_label}. Denominator for every row: {denominator} scored "
              "party-days.", ""]
    check_rows = []
    for key, label, estimator, unit in CHECKS:
        if key == "verifier":
            live_value = f"{report['live']['verifier_passed']} of {denominator}"
            cand_value = f"{report['candidate']['verifier_passed']} of {denominator}"
        else:
            live_value = f"{report['live']['guard_violation_party_days'][key]} of {denominator}"
            cand_value = (
                f"{report['candidate']['guard_violation_party_days'][key]} of {denominator}")
        check_rows.append([label, live_value, cand_value, estimator, unit])
    lines += _table(["Check", "Live (record)", "Candidate", "Estimator", "Unit"], check_rows)

    ceiling = report["fallback_rate_ceiling"]
    lines += [
        "", "### Fallback rate against the preregistered ceiling", "",
    ]
    lines += _table(
        ["Side", "Fallback party-days", "Denominator", "Rate", "Ceiling", "Within ceiling"],
        [["Live (record)", report["live"]["fallback_count"],
          report["live"]["fallback_rate_denominator"], report["live"]["fallback_rate"], ceiling,
          report["live"]["fallback_rate"] is not None
          and report["live"]["fallback_rate"] <= ceiling],
         ["Candidate", report["candidate"]["fallback_count"],
          report["candidate"]["fallback_rate_denominator"], report["candidate"]["fallback_rate"],
          ceiling, report["activation_gate"]["fallback_rate_passed"]]])
    lines += ["",
              f"Estimator: {report['candidate']['fallback_rate_estimator']}. Unit: "
              f"{report['candidate']['fallback_rate_unit']}. Window: {window_label}.", ""]

    moved = report["comparison"]["record_verifier_verdict_moved"]
    lines += [
        "## Verifier drift on the record side", "",
        f"Party-days where today's verifier disagrees with the verdict stored on the day: "
        f"**{moved} of {denominator}**. A non-zero count is a verifier-version finding about the "
        "record, not about either prompt, and it is reported rather than smoothed.",
        "",
        "## Composite quality, side by side", "",
        "Ranked by a stated score: one point for the verifier, one for each of the five clean "
        "guards, one for not falling back. Maximum 7. Ties break on day then party, so the "
        "selection is reproducible.",
        "",
    ]
    ranked = _rank(rows)
    if ranked:
        best, worst = quality_score(ranked[0]["candidate"]), quality_score(ranked[-1]["candidate"])
        if len(ranked) > 1 and best == worst:
            lines += [
                f"Every scored party-day ties at {best} of 7, so the two shown below are the "
                "first and last in the reproducible order, not a spread. A sample this small "
                "cannot separate the prompts on quality.",
                "",
            ]
        lines += _side_by_side(ranked[0], "Strongest day for the candidate")
        if len(ranked) > 1:
            lines += _side_by_side(ranked[-1], "Weakest day for the candidate")
        else:
            lines += ["_Only one scored party-day, so there is no weakest day distinct from the "
                      "strongest._", ""]
    else:
        lines += ["_No scored party-day. Nothing to compare._", ""]

    if evidence_rows is not None:
        covered = len({row["day"] for row in evidence_rows})
        lines += [
            "## Accumulated evidence", "",
            f"`data/derived/replay/evidence.jsonl` holds {len(evidence_rows)} party-days across "
            f"{covered} days, append-only, each row carrying its request hash beside the stored "
            "response.",
            "",
        ]

    lines += [
        "## Activation status", "",
    ]
    gate = report["activation_gate"]
    lines += _table(
        ["Condition", "Result"],
        [["Minimum sample (60 days, 200 party-days)", gate["minimum_sample_passed"]],
         ["Zero-tolerance checks clean", gate["zero_tolerance_checks_passed"]],
         [f"Fallback rate within {ceiling}", gate["fallback_rate_passed"]],
         ["Ready to activate", gate["ready"]]])
    lines += [
        "",
        "This report makes no flip recommendation. R-33.6 states the conditions and the gate "
        "decides. Until every condition above reads true on live evidence, P2 v1.4 and P3 v1.2 "
        "stay dark.",
        "",
        "## Reproduce", "",
        "```text",
        *REPRODUCE,
        "```",
        "",
    ]
    return "\n".join(lines)


def write(report: dict, path: Path, *, evidence_rows: list[dict] | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(report, evidence_rows=evidence_rows), encoding="utf-8", newline="\n")
    return path


def build(days_dir: Path | None = None, root: Path | None = None) -> dict:
    """Read live evidence when it exists; otherwise report the dry run, labelled as dry."""
    days_dir = Path(days_dir) if days_dir else config.DERIVED / "days"
    evidence = shadow_replay.load_evidence(root)
    return {"report": shadow_replay.run(days_dir), "evidence_rows": evidence}
