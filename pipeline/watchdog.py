"""Watchdog: the OUTERMOST liveness probe (Art. XVI, §deploy-hardening 2026-07-25).

THE HOLE THIS CLOSES. Both pipeline workflows end with a `if: failure()` dead-man step. That step
lives INSIDE the job, so it can only fire if a job was created. On 2026-07-25 the 11:30 UTC RUN B
concluded `startup_failure` at 12:31 with ZERO jobs: GitHub never created the job, the dead-man step
therefore never existed, and the day's two Bluesky threads, site render, and symmetry audit were
skipped in COMPLETE SILENCE. Michael found it by asking, not by being paged. It was the first
startup_failure in the repo's run history, so this failure mode had never been exercised — the
recovery path we thought we had, we did not have.

Art. XVI already required this: "Failure notifications belong at the outermost layer so a scheduled
workflow reports failures that occur before main()" and "A liveness probe observes advancing data
rather than its own process." The in-job dead-man satisfied neither for a run that never started.
This module is that outermost layer, and it runs in a SEPARATE workflow so its own liveness does not
depend on the workflow it is watching.

TWO INDEPENDENT SIGNAL CLASSES, because either one alone is blind:

  RUN-LEVEL (did the machine run?) — reads the Actions API run history. Catches startup_failure,
  cancellation, a disabled workflow, and GitHub silently dropping the cron (it does this to repos
  after 60 days of inactivity). This is the check that would have caught 2026-07-25.

  DATA-LEVEL (did the output advance?) — reads the COMMITTED manifests. Catches a run that is green
  but produced nothing, which no exit code can report. Art. XVI's "observes advancing data".

On 2026-07-25 the data-level checks alone would NOT have paged: `assemble-latest.json` still read
day 2026-07-23 and product_day was 2026-07-24, a lag of 1, which is normal before the morning pass
lands. Only the run-level check saw it. Both classes are load-bearing; neither is decoration.

WHAT THIS MODULE DOES NOT DO. It cannot detect the platform failing to schedule the WATCHDOG. That
residual risk needs a probe outside GitHub (an external heartbeat that pages when OnScript stops
checking in). Documented in docs/07-OPERATIONS.md P11; it needs an external account, so it is
Michael's to set up. Everything here is read-only: no commits, no pushes, no API spend.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, ops, util

# --- Thresholds. Each one states its estimator, unit, window, and derivation (Art. XVI). ---

# Age of the newest COMPLETED run, in hours, before we call the scheduler dead.
# Derivation: both pipelines run two passes/day. The widest healthy gap is RUN A's 19:30 -> 09:30
# UTC = 14h. Observed GitHub schedule delay reached 61 min on 2026-07-25 (11:30 cron dispatched
# 12:31), and the jobs themselves run up to their 60-min timeout. 14 + 1 + 1 = 16h worst healthy
# case; 26h leaves a 10h margin and still fires well inside the day after BOTH passes of a workflow
# produce nothing. Tighter than 26 risks paging on a slow Saturday; looser loses a full day.
RUN_MAX_AGE_HOURS = 26.0

# Age of collect-latest.json, in hours, before the ingest side is called stale. Same derivation:
# RUN A rewrites this manifest on EVERY successful pass (unlike assemble-latest, below).
COLLECT_MANIFEST_MAX_AGE_HOURS = 26.0

# How far the last finalized day may legitimately trail product_day, in days.
# Derivation: readiness.MAX_WAIT_DAYS = 2, so the gate may HOLD a not-yet-ready day for two days
# before force-finalizing it. Add 1 for the pass that finalizes day D-1 during day D. A lag of 3 is
# therefore reachable without anything being wrong; 4 means the gate stopped advancing.
FINAL_DAY_MAX_LAG_DAYS = 3

_OK, _ALARM = "ok", "alarm"


def _get(run: dict, *names):
    """Read a field across the two shapes the Actions API is consumed in: `gh api` returns
    snake_case (created_at), `gh run list --json` returns camelCase (createdAt). Accepting both
    means a future change of call site cannot silently blind the probe."""
    for n in names:
        if run.get(n) is not None:
            return run[n]
    return None


def _parse_iso(s: str | None) -> datetime | None:
    """Parse to an AWARE UTC instant. A naive input is read as UTC rather than left naive, because
    a naive/aware subtraction raises TypeError and would take the probe down instead of paging."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _finding(check: str, level: str, detail: str, **evidence) -> dict:
    return {"check": check, "level": level, "detail": detail, "evidence": evidence}


def _hours_since(then: datetime | None, now: datetime) -> float | None:
    if then is None:
        return None
    return round((now - then).total_seconds() / 3600.0, 2)


# ---------------------------------------------------------------------------
# RUN-LEVEL: did the machine actually run, and did it end green?
# ---------------------------------------------------------------------------
def check_runs(label: str, runs: list[dict] | None, now: datetime,
               *, max_age_hours: float = RUN_MAX_AGE_HOURS) -> list[dict]:
    """Judge one workflow's recent run history. `runs` is newest-first or any order; we sort.

    `None` means the caller did not supply history (local invocation without a token). That is
    reported as a NOTE, never as OK: a probe that cannot see must not claim health.
    """
    if runs is None:
        return [_finding(f"{label}_runs", "note", "no run history supplied — run-level checks skipped")]
    if not runs:
        return [_finding(f"{label}_runs", _ALARM,
                         f"{label}: the Actions API returned NO runs at all — workflow deleted, "
                         f"renamed, or Actions disabled for this repo")]

    completed = [r for r in runs if _get(r, "status") == "completed"]
    if not completed:
        # Everything in the window is still queued/in_progress. Not health, but not yet failure:
        # a long RUN A (63 min observed) legitimately looks like this. Report, do not page.
        return [_finding(f"{label}_runs", "note",
                         f"{label}: {len(runs)} run(s) in flight, none completed in the window")]

    latest = max(completed, key=lambda r: str(_get(r, "created_at", "createdAt") or ""))
    conclusion = _get(latest, "conclusion")
    created = _parse_iso(_get(latest, "created_at", "createdAt"))
    age = _hours_since(created, now)
    url = _get(latest, "html_url", "url") or ""
    out: list[dict] = []

    if conclusion != "success":
        # THE 2026-07-25 CHECK. `startup_failure` lands here, and so does cancelled/timed_out/
        # failure. Anything that is not success is a day at risk, and it self-clears the moment a
        # later run succeeds, so no state file is needed to stop repeat pages.
        out.append(_finding(f"{label}_conclusion", _ALARM,
                            f"{label}: last completed run concluded '{conclusion}', not success",
                            conclusion=conclusion, run_url=url, age_hours=age))
    if age is None:
        # The API always carries created_at. If it does not, staleness is UNKNOWABLE, and a probe
        # that cannot judge must not report health (same rule as absent history, above).
        out.append(_finding(f"{label}_scheduler", _ALARM,
                            f"{label}: newest completed run has no readable created_at, so its age "
                            f"cannot be judged", raw=_get(latest, "created_at", "createdAt")))
    elif age > max_age_hours:
        # No successful dispatch in a full cadence window. GitHub disables cron on repos after 60
        # days without activity; a schedule that silently stops looks exactly like this.
        out.append(_finding(f"{label}_scheduler", _ALARM,
                            f"{label}: newest completed run is {age}h old (>{max_age_hours}h) — "
                            f"the schedule appears to have stopped firing",
                            age_hours=age, threshold_hours=max_age_hours, run_url=url))
    if not out:
        out.append(_finding(f"{label}_runs", _OK,
                            f"{label}: last completed run succeeded {age}h ago", age_hours=age))
    return out


# ---------------------------------------------------------------------------
# DATA-LEVEL: did the committed output advance? (Art. XVI liveness)
# ---------------------------------------------------------------------------
def check_manifests(derived: Path, now: datetime, product_day: str) -> list[dict]:
    """Read the committed record, not the process. A green run that wrote nothing fails here."""
    out: list[dict] = []
    mdir = Path(derived) / "manifest"

    collect = util.read_json(mdir / "collect-latest.json", None)
    if not collect:
        out.append(_finding("collect_manifest", _ALARM,
                            "collect-latest.json is missing — RUN A has never committed here"))
    else:
        age = _hours_since(_parse_iso(collect.get("generated_at")), now)
        if age is None:
            out.append(_finding("collect_manifest", _ALARM,
                                "collect-latest.json has no readable generated_at",
                                generated_at=collect.get("generated_at")))
        elif age > COLLECT_MANIFEST_MAX_AGE_HOURS:
            out.append(_finding("collect_freshness", _ALARM,
                                f"ingest is stale: collect-latest.json is {age}h old "
                                f"(>{COLLECT_MANIFEST_MAX_AGE_HOURS}h)",
                                age_hours=age, run_id=collect.get("run_id")))
        else:
            out.append(_finding("collect_freshness", _OK, f"ingest fresh ({age}h)", age_hours=age))

    assemble = util.read_json(mdir / "assemble-latest.json", None)
    if not assemble or not assemble.get("day"):
        out.append(_finding("assemble_manifest", _ALARM,
                            "assemble-latest.json is missing or has no day — nothing was ever "
                            "finalized"))
        return out

    final_day = assemble["day"]
    try:
        lag = (datetime.fromisoformat(product_day).date()
               - datetime.fromisoformat(final_day).date()).days
    except ValueError:
        out.append(_finding("publication_advance", _ALARM,
                            f"assemble-latest.json day is unparseable: {final_day!r}"))
        return out

    if lag > FINAL_DAY_MAX_LAG_DAYS:
        out.append(_finding("publication_advance", _ALARM,
                            f"the series has stopped advancing: last finalized day {final_day} "
                            f"trails product day {product_day} by {lag}d "
                            f"(>{FINAL_DAY_MAX_LAG_DAYS}d, the readiness gate's own hold ceiling)",
                            final_day=final_day, product_day=product_day, lag_days=lag))
    else:
        out.append(_finding("publication_advance", _OK,
                            f"last finalized day {final_day}, {lag}d behind product day",
                            final_day=final_day, lag_days=lag))

    # A finalized day always leaves a post manifest, in dry-run as well as live (the manifests
    # from 2026-07-13 predate POSTING_ENABLED going true on 2026-07-21). A finalized day with no
    # post manifest means assemble finished the data leg and lost the publication leg silently.
    post = mdir / f"post-{final_day}.json"
    if not post.exists():
        out.append(_finding("post_manifest", _ALARM,
                            f"day {final_day} was finalized but {post.name} does not exist — the "
                            f"posting leg did not complete", final_day=final_day))
    else:
        out.append(_finding("post_manifest", _OK, f"{post.name} present", final_day=final_day))
    return out


def evaluate(*, derived: Path, now: datetime, product_day: str,
             collect_runs: list[dict] | None = None,
             assemble_runs: list[dict] | None = None) -> dict:
    """Full probe. Returns {findings, alarms, ok}. Pure: no network, no writes, no clock reads."""
    findings = (check_runs("collect", collect_runs, now)
                + check_runs("assemble", assemble_runs, now)
                + check_manifests(derived, now, product_day))
    alarms = [f for f in findings if f["level"] == _ALARM]
    return {"findings": findings, "alarms": alarms, "ok": not alarms,
            "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "product_day": product_day}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load_runs(path: str | None) -> list[dict] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("workflow_runs", data) if isinstance(data, dict) else data


def _report(result: dict) -> str:
    lines = [f"OnScript watchdog {result['checked_at']} (product day {result['product_day']})"]
    for f in result["findings"]:
        lines.append(f"  [{f['level'].upper():5}] {f['check']}: {f['detail']}")
    lines.append(f"  {len(result['alarms'])} alarm(s)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OnScript outermost liveness probe")
    ap.add_argument("--collect-runs", help="JSON file of collect.yml run history (gh api)")
    ap.add_argument("--assemble-runs", help="JSON file of assemble.yml run history (gh api)")
    ap.add_argument("--derived", default=str(config.DERIVED))
    ap.add_argument("--now", help="ISO instant to judge against (testing)")
    ap.add_argument("--product-day", help="override product day (testing)")
    ap.add_argument("--no-notify", action="store_true", help="print only, never page")
    args = ap.parse_args(argv)

    now = _parse_iso(args.now) or datetime.now(timezone.utc)
    result = evaluate(derived=Path(args.derived), now=now,
                      product_day=args.product_day or util.product_day(),
                      collect_runs=_load_runs(args.collect_runs),
                      assemble_runs=_load_runs(args.assemble_runs))
    report = _report(result)
    print(report)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:  # pragma: no cover - Actions only
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Watchdog\n\n```\n{report}\n```\n")

    for f in result["alarms"]:  # annotate so the run page carries the reason, not just ntfy
        print(f"::error::watchdog {f['check']}: {f['detail']}")

    if result["alarms"] and not args.no_notify:
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        body = "\n".join(f"- {f['detail']}" for f in result["alarms"])
        if repo:
            body += f"\n\nhttps://github.com/{repo}/actions"
        ops.ntfy(f"OnScript watchdog: {len(result['alarms'])} alarm(s)", body, priority="high")

    # Exit 0 even when alarms fire: the probe did its job, and the page has already been sent. A
    # non-zero exit here would trip the workflow's own `if: failure()` dead-man and page a SECOND
    # time for one incident. The job goes red only when the watchdog ITSELF breaks, which is the
    # one condition its in-job dead-man is there to report. One alert per failure mode.
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
