"""The governance guard's decision table, tested against the live hook module.

The guard is harness configuration on the operating path of every session, so it
gets tests like any other production path (docs/37 rules 1 and 2). The tests load
the module from its committed location so they exercise the file the hook wiring
in .claude/settings.json actually runs, never a copy.
"""
import importlib.util
from datetime import date
from pathlib import Path

_GUARD = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "governance_guard.py"
_spec = importlib.util.spec_from_file_location("governance_guard", _GUARD)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

SUMMER = date(2026, 7, 29)
FROZEN = date(2026, 10, 20)


def _bash(cmd, today=SUMMER):
    return guard.decide("Bash", {"command": cmd}, today=today)


def _edit(path, today=SUMMER):
    return guard.decide("Edit", {"file_path": path}, today=today)


def test_git_add_all_forms_are_denied():
    for cmd in ("git add -A", "git add --all", "git add .", "cd x && git add -A"):
        decision = _bash(cmd)
        assert decision is not None and decision[0] == "deny", cmd


def test_git_add_explicit_paths_pass():
    assert _bash("git add docs/26-SESSION-HISTORY.md CLAUDE.md") is None


def test_bare_python_is_denied_and_miniconda_passes():
    assert _bash("python tests/run_tests.py")[0] == "deny"
    assert _bash("cd tests && python run_tests.py")[0] == "deny"
    assert _bash("C:/ProgramData/miniconda3/python.exe tests/run_tests.py") is None


def test_git_push_asks_and_force_push_is_denied():
    assert _bash("git push origin main")[0] == "ask"
    assert _bash("git push --force origin main")[0] == "deny"
    assert _bash("git push -f")[0] == "deny"


def test_workflow_dispatch_asks_in_summer_and_is_denied_in_freeze():
    assert _bash("gh workflow run assemble.yml")[0] == "ask"
    assert _bash("gh workflow run assemble.yml", today=FROZEN)[0] == "deny"


def test_generated_trees_ask_on_stage_and_edit():
    assert _bash("git add site/public/index.html")[0] == "ask"
    assert _bash("git commit -m x data/derived/foo.json")[0] == "ask"
    assert _edit(r"C:\Users\bobdo\projects\polispeak\site\public\index.html")[0] == "ask"
    assert _edit("data/derived/audit.json")[0] == "ask"


def test_prompt_and_config_edits_ask_in_summer_and_deny_in_freeze():
    assert _edit("pipeline/prompts/p2.txt")[0] == "ask"
    assert _edit("pipeline/prompts/p2.txt", today=FROZEN)[0] == "deny"
    assert _edit("pipeline/config.py")[0] == "ask"
    assert _edit("pipeline/config.py", today=FROZEN)[0] == "deny"
    assert _edit("pipeline/prompts/README.md") is None


def test_workflow_edits_pass_in_summer_and_deny_in_freeze():
    assert _edit(".github/workflows/assemble.yml") is None
    assert _edit(".github/workflows/assemble.yml", today=FROZEN)[0] == "deny"


def test_constitution_edit_asks():
    assert _edit("docs/06-CONSTITUTION.md")[0] == "ask"


def test_ordinary_work_is_untouched():
    assert _bash("git status") is None
    assert _bash("git commit -m 'docs: session record' docs/26-SESSION-HISTORY.md") is None
    assert _edit("pipeline/collect.py") is None
    assert _edit("docs/26-SESSION-HISTORY.md") is None


def test_freeze_window_boundaries():
    assert not guard.in_freeze(date(2026, 10, 14))
    assert guard.in_freeze(date(2026, 10, 15))
    assert guard.in_freeze(date(2026, 11, 10))
    assert not guard.in_freeze(date(2026, 11, 11))


def test_unknown_tools_and_empty_input_fail_open():
    assert guard.decide("WebFetch", {"url": "https://example.com"}) is None
    assert guard.decide("Bash", {}) is None
