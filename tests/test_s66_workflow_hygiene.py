"""S66-6 acceptance: three ways CI could fail quietly, closed.

docs/39. (a) post.yml triggers on the assemble workflow by DISPLAY NAME, and a display name is
prose that gets rewritten; a rename would stop posting with every workflow green and nothing to
look at. (b) assemble.yml pasted a dispatch input straight into a run block, so an
operator-supplied string was the shell's to parse. (c) Constitution Article VIII promises the
instrument does not move from Oct 15 through Nov 10, and the only enforcement was prose plus a
Claude Code hook, which sees one operator's session and not CI, another machine, or a merge.

The freeze check ships inert. These tests prove the date logic in both directions rather than
waiting until October to find out.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from pipeline import config, freeze_window


WORKFLOWS = Path(config.REPO_ROOT) / ".github" / "workflows"


def _text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


# --- (a) the trigger is asserted by path, not by display name --------------------------------

def test_the_post_job_asserts_its_trigger_by_workflow_path():
    text = _text("post.yml")
    assert "github.event.workflow_run.path" in text
    assert ".github/workflows/assemble.yml" in text
    # It is the FIRST step, so a wrong trigger cannot reach the posting credentials.
    steps = text.index("    steps:")
    assert text.index("workflow_run.path") < text.index("actions/checkout", steps)
    assert text.index("workflow_run.path") < text.index("post_bluesky.py")


def test_the_asserted_path_is_a_workflow_that_exists():
    assert (WORKFLOWS / "assemble.yml").exists()
    # The display name the workflow_run filter matches must still be the one assemble.yml carries,
    # otherwise posting is already broken and this test is the only thing that would say so.
    assert 'workflows: ["RUN B assemble"]' in _text("post.yml")
    assert _text("assemble.yml").splitlines()[0] == "name: RUN B assemble"


# --- (b) dispatch input reaches the shell through env ----------------------------------------

def test_no_workflow_interpolates_a_dispatch_input_into_a_run_block():
    offenders = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "github.event.inputs." in line and "${{" in line and ":" not in line.split("${{")[0]:
                offenders.append(f"{path.name}:{number}")
    assert not offenders, offenders


def test_the_assemble_day_input_arrives_as_an_environment_variable():
    text = _text("assemble.yml")
    assert "DAY: ${{ github.event.inputs.day }}" in text
    assert 'python pipeline/run_assemble.py --day "$DAY"' in text


# --- (c) the freeze window ---------------------------------------------------------------------

def test_the_window_is_october_fifteen_through_november_ten_inclusive():
    assert freeze_window.in_freeze(date(2026, 10, 14)) is False
    assert freeze_window.in_freeze(date(2026, 10, 15)) is True
    assert freeze_window.in_freeze(date(2026, 10, 31)) is True
    assert freeze_window.in_freeze(date(2026, 11, 10)) is True
    assert freeze_window.in_freeze(date(2026, 11, 11)) is False
    assert freeze_window.in_freeze(date(2027, 10, 20)) is True   # any year


def test_the_check_is_inert_outside_the_window():
    changed = ["pipeline/config.py", "pipeline/prompts/daily.txt", ".github/workflows/post.yml"]
    assert freeze_window.frozen_changes(changed, date(2026, 8, 9)) == []
    code, message = freeze_window.report(changed, date(2026, 8, 9))
    assert code == 0 and "outside the election freeze" in message


def test_every_frozen_path_class_is_refused_inside_the_window():
    inside = date(2026, 10, 20)
    for path in ("pipeline/prompts/daily.txt", "pipeline/config.py",
                 ".github/workflows/collect.yml", "./pipeline/config.py",
                 "pipeline\\config.py"):
        code, _message = freeze_window.report([path], inside)
        assert code == 1, path


def test_ordinary_work_still_passes_inside_the_window():
    inside = date(2026, 10, 20)
    changed = ["pipeline/site.py", "docs/26-SESSION-HISTORY.md", "tests/test_site.py",
               "data/derived/days/2026-10-20.json", "pipeline/prompts.py"]
    code, message = freeze_window.report(changed, inside)
    assert code == 0 and "touches no frozen path" in message


def test_a_refusal_names_the_paths_and_the_article():
    code, message = freeze_window.report(
        ["pipeline/config.py", "pipeline/site.py"], date(2026, 10, 20))
    assert code == 1
    assert "pipeline/config.py" in message
    assert "pipeline/site.py" not in message
    assert "Article VIII" in message


# --- one window, two enforcers ----------------------------------------------------------------

def test_the_governance_guard_and_the_pipeline_agree_on_the_window():
    """The hook keeps its own dates because it runs standalone; they may not drift (rule 1)."""
    guard = Path(config.REPO_ROOT) / ".claude" / "hooks" / "governance_guard.py"
    if not guard.exists():
        return
    namespace: dict = {}
    source = guard.read_text(encoding="utf-8")
    for line in source.splitlines():
        if line.startswith(("FREEZE_START", "FREEZE_END")):
            exec(line, namespace)  # noqa: S102 - two literal tuples from a repo-owned file
    assert namespace.get("FREEZE_START") == freeze_window.FREEZE_START
    assert namespace.get("FREEZE_END") == freeze_window.FREEZE_END


def test_the_workflow_runs_the_owning_module():
    text = _text("freeze-check.yml")
    assert "python -m pipeline.freeze_window --stdin" in text
    assert "on:\n  push:" in text
    assert "fetch-depth: 0" in text          # the diff needs history
    assert "permissions:\n  contents: read" in text
