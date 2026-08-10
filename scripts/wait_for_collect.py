"""RUN B waits out an in-flight RUN A before it checks anything out.

WHY THIS EXISTS ALONGSIDE THE CONCURRENCY GROUP. collect.yml and assemble.yml both declare
`concurrency: group: onscript-pipeline` with `cancel-in-progress: false`, and on 2026-08-10 that
did not serialize them. RUN B (31386662898) was created at 12:09:00Z while RUN A, created at
10:41:20Z, was still in_progress. RUN A pushed its data commit cbb280b at 12:18:15Z; a hundred
seconds later RUN B's push step fetched 752fe29..cbb280b, rebased its own data commit onto it, and
died on CONFLICT (add/add) in data/derived/days/2026-08-09.json, because both runs had ADDED that
path from checkouts that did not carry it. The same overlap sits in the 2026-08-08 log (RUN A
10:00:48Z for 2h11m49s against RUN B 11:55:22Z for 18m55s) and cost nothing there only because the
two runs happened to write different day files. An observed overlap under identical stanzas is not
a property to build on, so the wait is explicit.

WHY IT RUNS BEFORE THE AUTHORITATIVE CHECKOUT. Waiting alone would not have saved the run. A
scheduled workflow checks out `github.sha`, the tip of the default branch at the moment the run was
CREATED, so RUN B's tree would still have been 752fe29 after the wait and its commit would still
have ADDED the day file RUN A added at 12:18:15Z. The wait buys nothing unless the tree is then
resolved from `main`. assemble.yml does both, in that order.

FAIL CLOSED, WITH NO FOURTH OUTCOME. No live RUN A: proceed. A live RUN A: keep waiting. The bound
or the API error budget exhausted: exit non-zero, and the workflow-level dead-man fires. `proceed`
is reachable only from a successful poll that saw nothing running. An unreadable API is an unknown
state, and an unknown state never proceeds into a race we know is there.

DAY ONE (docs/37 rule 4). The transition path for existing production state is that there is none
to transition. On the first run under this gate, and on every run where collect is not active
(the ordinary case, since the 11:30 and 21:30 passes normally begin after collect has finished),
the first poll sees nothing running and the step exits 0 in about a second. The gate adds latency
only in the situation it was written for.
"""
from __future__ import annotations

import json
import os
import subprocess
import time

# By FILE, never by display name. docs/39 and tests/test_s66_workflow_hygiene: a display name is
# prose that gets rewritten, and post.yml already learned this the expensive way. The Actions API
# accepts a workflow file name wherever it accepts a workflow id, so a rename of collect.yml turns
# into a 404, which this script reports as an unknown state and refuses to proceed on.
COLLECT_WORKFLOW = "collect.yml"

# Everything the Actions API calls not-yet-finished. Listed rather than derived from `!= completed`
# so a new status string cannot silently read as idle.
ACTIVE_STATUSES = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})

POLL_SECONDS = 60

# 150 minutes. Collect's own job timeout is 240, but the gap between the crons makes 150 the
# practical bound: RUN A starts at 09:30 and RUN B at 11:30, so a RUN A that is still going 150
# minutes after RUN B began has run 4h30m against a slowest-on-record 2h11m49s (2026-08-08) and is
# stuck, not slow. Waiting past that trades a loud failure for a silent one. assemble.yml's job
# budget is sized to hold this bound plus the assemble work; the two move together.
BOUND_SECONDS = 150 * 60

# Consecutive failed polls tolerated before the gate gives up. A single API blip inside a
# two-and-a-half hour window is noise; three in a row is the API, and neither is a licence to run.
ERROR_BUDGET = 3


def active_runs(payload: dict | None) -> list:
    """The live RUN A runs in one Actions API page."""
    runs = (payload or {}).get("workflow_runs") or []
    return [r for r in runs if str(r.get("status") or "").lower() in ACTIVE_STATUSES]


def describe(runs) -> str:
    return ", ".join(
        f"#{r.get('id')} {r.get('status')} (created {r.get('created_at')})" for r in runs
    ) or "none"


def decide(observation: dict, *, elapsed_s: float, bound_s: float = BOUND_SECONDS,
           error_budget: int = ERROR_BUDGET) -> dict:
    """What should RUN B do with one poll result? The whole decision, and it is pure.

    `observation` is {"ok": True, "active": [...]} or {"ok": False, "error": str,
    "consecutive_errors": int}. Returns {"action", "reason"} with action in proceed / wait /
    retry / fail. The proceed branch is written first and reads first on purpose: it is the only
    door out of this gate that is not a failure, and it opens only on a poll that succeeded and
    saw nothing running.
    """
    if observation.get("ok") and not observation.get("active"):
        return {"action": "proceed",
                "reason": "no RUN A (collect) run is queued or in progress"}
    if elapsed_s >= bound_s:
        waited = int(bound_s // 60)
        if observation.get("ok"):
            return {"action": "fail",
                    "reason": (f"RUN A is still live after {waited} minutes of waiting "
                               f"({describe(observation.get('active') or [])}). Refusing to "
                               f"assemble beside it: two runs adding the same day file rebase "
                               f"into an add/add conflict (2026-08-10).")}
        return {"action": "fail",
                "reason": (f"the runs API has been unreadable for {waited} minutes "
                           f"({observation.get('error')}). RUN A's state is unknown and an "
                           f"unknown state never proceeds.")}
    if not observation.get("ok"):
        seen = int(observation.get("consecutive_errors") or 1)
        if seen >= error_budget:
            return {"action": "fail",
                    "reason": (f"the runs API failed {seen} polls in a row "
                               f"({observation.get('error')}). RUN A's state is unknown and an "
                               f"unknown state never proceeds.")}
        return {"action": "retry",
                "reason": (f"the runs API failed (attempt {seen} of {error_budget}): "
                           f"{observation.get('error')}")}
    return {"action": "wait",
            "reason": f"RUN A is live: {describe(observation.get('active') or [])}"}


def poll(repo: str) -> dict:
    """One observation of RUN A's state. Never raises: a failed call is an observation, not a crash.

    per_page=50 without a status filter, because the API takes one status per query and the page is
    ordered newest first: anything live is inside the last fifty runs of this workflow by a wide
    margin, and filtering here rather than in the query keeps the live-status set in one place.
    """
    url = f"repos/{repo}/actions/workflows/{COLLECT_WORKFLOW}/runs?per_page=50"
    try:
        done = subprocess.run(["gh", "api", url], capture_output=True, text=True, timeout=60)
    except Exception as e:  # noqa: BLE001 - gh missing, hung, or killed; all are unknown state
        return {"ok": False, "error": f"gh api did not return: {e!r}"}
    if done.returncode != 0:
        detail = (done.stderr or done.stdout or "").strip().replace("\n", " ")[:400]
        return {"ok": False, "error": f"gh api exited {done.returncode}: {detail}"}
    try:
        return {"ok": True, "active": active_runs(json.loads(done.stdout))}
    except Exception as e:  # noqa: BLE001 - a body that will not parse is an unknown state
        return {"ok": False, "error": f"gh api returned unparseable JSON: {e!r}"}


def main(*, repo: str | None = None, observe=None, sleep=time.sleep, clock=time.monotonic,
         bound_s: float = BOUND_SECONDS, poll_seconds: float = POLL_SECONDS,
         error_budget: int = ERROR_BUDGET) -> int:
    """Poll until RUN A is idle, or fail loudly. Returns a process exit code.

    The collaborators are injected so the tests drive the same loop the workflow runs rather than a
    copy of it (docs/37 rule 1).
    """
    repo = repo or os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY") or ""
    if observe is None:
        if not repo:
            print("::error::neither REPO nor GITHUB_REPOSITORY is set, so RUN A's state cannot "
                  "be read. Refusing to assemble beside an unknown collect.", flush=True)
            return 1
        def observe():  # noqa: E306 - the default collaborator, bound to the repo just resolved
            return poll(repo)

    started = clock()
    consecutive_errors = 0
    cycle = 0
    print(f"[serializer] waiting out any live {COLLECT_WORKFLOW} run in {repo or '(unset)'}; "
          f"poll {int(poll_seconds)}s, bound {int(bound_s // 60)} min", flush=True)
    while True:
        cycle += 1
        elapsed = clock() - started
        observation = dict(observe() or {})
        consecutive_errors = 0 if observation.get("ok") else consecutive_errors + 1
        observation["consecutive_errors"] = consecutive_errors
        verdict = decide(observation, elapsed_s=elapsed, bound_s=bound_s,
                         error_budget=error_budget)
        print(f"[serializer] cycle {cycle}, {int(elapsed)}s elapsed of {int(bound_s)}s: "
              f"{verdict['action']} :: {verdict['reason']}", flush=True)
        if verdict["action"] == "proceed":
            return 0
        if verdict["action"] == "fail":
            print(f"::error::RUN B refused to start: {verdict['reason']}", flush=True)
            return 1
        sleep(poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
