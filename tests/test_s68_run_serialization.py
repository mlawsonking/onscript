"""S68 acceptance: RUN B refuses to run beside RUN A, and refuses on an unknown state.

The incident. On 2026-08-10 RUN B (31386662898) was created at 12:09:00Z while RUN A, created at
10:41:20Z, was still in_progress, under a concurrency group both workflows share with
cancel-in-progress: false. RUN A pushed cbb280b at 12:18:15Z. At 12:19:58Z RUN B's push step
rebased its own data commit onto it and died on CONFLICT (add/add) in
data/derived/days/2026-08-09.json, because both runs had ADDED that path from checkouts that did
not carry it. The whole assemble evaporated with the failed run.

These tests drive scripts/wait_for_collect.py itself, loop included, with the clock and the API
injected. There is no second implementation of the decision to test against (docs/37 rule 1), and
the last three tests assert the workflow against the live module's constants rather than against a
restatement of them.
"""
from __future__ import annotations

import importlib.util
import io
import re
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ASSEMBLE = ROOT / ".github" / "workflows" / "assemble.yml"
SCRIPT_RELPATH = "scripts/wait_for_collect.py"


def _module():
    """The live script, loaded as a module. scripts/ is not a package."""
    path = ROOT / SCRIPT_RELPATH
    spec = importlib.util.spec_from_file_location("wait_for_collect", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


W = _module()


def _live(status="in_progress", run_id=31332869180):
    return {"id": run_id, "status": status, "created_at": "2026-08-10T10:41:20Z"}


def _ok(*runs):
    return {"ok": True, "active": list(runs)}


def _err(message="gh api exited 1: HTTP 500", consecutive=1):
    return {"ok": False, "error": message, "consecutive_errors": consecutive}


# --- the decision, one poll at a time ---------------------------------------------------------

def test_a_live_collect_makes_run_b_wait():
    verdict = W.decide(_ok(_live()), elapsed_s=0)
    assert verdict["action"] == "wait"
    # The reason has to name the run, or a 150-minute log is 150 identical lines.
    assert "31332869180" in verdict["reason"] and "in_progress" in verdict["reason"]


def test_a_quiet_api_lets_run_b_proceed_immediately():
    """DAY ONE (docs/37 rule 4). Nothing to transition: the usual case is zero live collects, and
    the gate exits 0 on its first poll."""
    verdict = W.decide(_ok(), elapsed_s=0)
    assert verdict["action"] == "proceed"


def test_only_unfinished_statuses_count_as_a_live_collect():
    payload = {"workflow_runs": [
        {"id": 1, "status": "completed", "conclusion": "success"},
        {"id": 2, "status": "completed", "conclusion": "cancelled"},
        {"id": 3, "status": "in_progress"},
        {"id": 4, "status": "queued"},
        {"id": 5, "status": "waiting"},
    ]}
    assert [r["id"] for r in W.active_runs(payload)] == [3, 4, 5]
    assert W.active_runs({"workflow_runs": []}) == []
    assert W.active_runs(None) == []


def test_past_the_bound_a_live_collect_fails_loud_and_says_what_it_waited_for():
    verdict = W.decide(_ok(_live()), elapsed_s=W.BOUND_SECONDS)
    assert verdict["action"] == "fail"
    assert "150 minutes" in verdict["reason"]
    assert "31332869180" in verdict["reason"]
    assert "add/add" in verdict["reason"]


def test_an_api_error_retries_below_the_budget_and_never_proceeds():
    for seen in range(1, W.ERROR_BUDGET):
        verdict = W.decide(_err(consecutive=seen), elapsed_s=0)
        assert verdict["action"] == "retry", seen
        assert "HTTP 500" in verdict["reason"]


def test_an_api_error_at_the_budget_fails_loud():
    verdict = W.decide(_err(consecutive=W.ERROR_BUDGET), elapsed_s=0)
    assert verdict["action"] == "fail"
    assert "unknown state never proceeds" in verdict["reason"]


def test_past_the_bound_an_unreadable_api_fails_on_the_unknown_state_not_on_the_wait():
    verdict = W.decide(_err(consecutive=1), elapsed_s=W.BOUND_SECONDS)
    assert verdict["action"] == "fail"
    assert "unreadable" in verdict["reason"]


def test_no_failed_poll_can_ever_produce_proceed():
    """The property, not an example: `proceed` is reachable only from a successful observation."""
    for elapsed in (0, 60, W.BOUND_SECONDS - 1, W.BOUND_SECONDS, W.BOUND_SECONDS * 2):
        for seen in (1, 2, 3, 9):
            assert W.decide(_err(consecutive=seen), elapsed_s=elapsed)["action"] != "proceed"
    # And an ok poll that still sees a live run never proceeds either.
    for elapsed in (0, 60, W.BOUND_SECONDS):
        assert W.decide(_ok(_live()), elapsed_s=elapsed)["action"] != "proceed"


# --- the loop that the workflow actually runs --------------------------------------------------

class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def _run(observations, *, bound_s=W.BOUND_SECONDS):
    """Drive main() with a scripted API and a clock that only the sleeps advance."""
    clock, slept, seen = _Clock(), [], iter(observations)

    def observe():
        return next(seen)

    def sleep(seconds):
        slept.append(seconds)
        clock.now += seconds

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = W.main(repo="mlawsonking/onscript", observe=observe, sleep=sleep, clock=clock,
                      bound_s=bound_s, poll_seconds=60)
    return code, slept, buffer.getvalue()


def test_the_loop_waits_out_a_live_collect_and_then_proceeds():
    code, slept, log = _run([_ok(_live()), _ok(_live()), _ok()])
    assert code == 0
    assert slept == [60, 60], "one poll interval per live observation, and none after proceeding"
    # A loud line per cycle, not one summary at the end.
    assert len(re.findall(r"^\[serializer\] cycle ", log, re.M)) == 3
    assert "proceed" in log


def test_the_loop_proceeds_on_the_first_poll_when_nothing_is_running():
    code, slept, log = _run([_ok()])
    assert code == 0 and slept == []
    assert "no RUN A (collect) run is queued or in progress" in log


def test_the_loop_exits_non_zero_at_the_bound_with_a_github_error_annotation():
    # A bound of two poll intervals: two waits, and the third cycle is past it.
    code, slept, log = _run([_ok(_live())] * 4, bound_s=120)
    assert code == 1
    assert slept == [60, 60]
    assert "::error::RUN B refused to start:" in log


def test_the_loop_recovers_from_a_transient_api_error_rather_than_failing_on_it():
    code, slept, log = _run([_err(), _ok(_live()), _ok()])
    assert code == 0 and slept == [60, 60]
    assert "retry" in log
    # The counter resets on a good poll, so scattered blips never accumulate into a refusal.
    assert "::error::" not in log


def test_the_loop_fails_after_the_error_budget_of_consecutive_failures():
    code, slept, log = _run([_err()] * (W.ERROR_BUDGET + 2))
    assert code == 1
    assert len(slept) == W.ERROR_BUDGET - 1, "it stops sleeping the moment the budget is spent"
    assert "::error::" in log


def test_an_unresolvable_repository_refuses_rather_than_polling_nothing():
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = W.main(repo="", observe=None, sleep=lambda _s: None,
                      clock=_Clock(), bound_s=60)
    assert code == 1
    assert "::error::" in buffer.getvalue()


# --- the workflow, asserted against the live module -------------------------------------------

def test_the_workflow_names_a_collect_workflow_file_that_exists():
    """By path, never by display name (docs/39, tests/test_s66_workflow_hygiene)."""
    assert (ROOT / ".github" / "workflows" / W.COLLECT_WORKFLOW).exists()


def test_assemble_runs_the_serializer_before_the_authoritative_checkout():
    text = ASSEMBLE.read_text(encoding="utf-8")
    assert f"python3 {SCRIPT_RELPATH}" in text
    # The wait is worthless unless the tree is resolved from main AFTER it: a scheduled run
    # otherwise keeps the github.sha tree that produced the add/add conflict.
    assert "ref: main" in text
    assert text.index(SCRIPT_RELPATH) < text.index("ref: main")
    # And the API the gate reads has to be permitted, or it 403s into a refusal every day.
    assert re.search(r"(?m)^permissions:\n(?:\s*#.*\n)*\s*actions: read$", text)


def test_the_job_budget_covers_the_serializer_bound_plus_the_assemble_work():
    """A job timeout CANCELS, and a cancelled job skips the `if: failure()` dead-man. If the bound
    can outlive the budget, the gate converts a loud failure into a silent one."""
    text = ASSEMBLE.read_text(encoding="utf-8")
    # Editing a job header by hand is how a runner declaration goes missing, and YAML that still
    # parses is not a workflow that still runs. This session dropped it once.
    assert re.search(r"(?m)^    runs-on: \S+$", text)
    job = int(re.search(r"(?m)^    timeout-minutes: (\d+)$", text).group(1))
    step = int(re.search(r"(?m)^        timeout-minutes: (\d+)$", text).group(1))
    bound_minutes = W.BOUND_SECONDS / 60
    assert step > bound_minutes, "the step timeout must not fire before the gate's own bound"
    assert job >= step + 55, "the wait can consume its whole bound and the assemble still has to fit"
