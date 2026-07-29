"""Governance guard: a PreToolUse hook enforcing the CLAUDE.md standing rules.

This script is the mechanical form of rules that previously lived only as prose.
Prose rules depend on every session reading and obeying them; this hook makes the
harness refuse or confirm instead. It runs on every Bash, PowerShell, and file-edit
tool call in a Claude Code session (wired in .claude/settings.json). Hooks run in
every permission mode, including bypass-permissions, so the deny rules here hold
even when the permission system is off.

Decisions, strongest wins:
  deny  A hard invariant. The call is refused with the rule and its source cited.
  ask   A release act or a guarded surface. The operator confirms in the session.
  None  No rule applies; the normal permission flow decides.

Rules enforced, each citing its source:
  1. Never git add -A, --all, or bare "git add ." (CLAUDE.md standing rules;
     AGENTS.md and tests/_tmp_watchdog/ stay untracked).
  2. Bare python is a 0-byte stub on the operator machine; the interpreter is
     C:/ProgramData/miniconda3/python.exe (CLAUDE.md, local development).
  3. git push, workflow dispatch, and deploys are release acts and belong to
     Michael; sessions get a confirm prompt, never a silent pass (CLAUDE.md;
     docs/27). Force pushes are refused outright.
  4. Staging or committing site/public or data/derived gets a confirm prompt:
     never regenerated as a side effect of validation (CLAUDE.md standing rules).
  5. Edits to pipeline/prompts/ (prompt bytes are versioned runtime behavior,
     docs/25 section 2), pipeline/config.py (flags and thresholds; flips are
     Michael's), and docs/06-CONSTITUTION.md (Article XV process) get a confirm
     prompt.
  6. During the election freeze, Oct 15 through Nov 10 (Constitution Article
     VIII), edits to prompts, config, and workflows are refused, as are gh
     workflow/variable/secret commands. This enforces the mechanical subset of
     the freeze; the constitutional scope is wider and still binds.

Failure posture: the guard fails open. If it cannot parse its input it reports
on stderr and allows the normal flow, because a guard that blocks every tool
call on its own defect is an authored outage (docs/37 rule 4).
"""

import json
import re
import sys
from datetime import date

MINICONDA = "C:/ProgramData/miniconda3/python.exe"

FREEZE_START = (10, 15)
FREEZE_END = (11, 10)

COMMAND_TOOLS = {
    "Bash",
    "PowerShell",
    "mcp__Windows-MCP__PowerShell",
    "mcp__plugin_desktop-commander_desktop-commander__start_process",
    "mcp__plugin_desktop-commander_desktop-commander__interact_with_process",
}

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

GENERATED_TREES = ("site/public/", "data/derived/")


def in_freeze(today=None):
    """Constitution Article VIII: Oct 15 through Nov 10, inclusive, any year."""
    t = today or date.today()
    return FREEZE_START <= (t.month, t.day) <= FREEZE_END


def _segments(command):
    """Split a shell command into rough segments so chained commands are seen."""
    return [s.strip() for s in re.split(r"[;&|\n]+", command) if s.strip()]


def _check_command(command, today=None):
    worst = None
    for seg in _segments(command):
        d = _check_segment(seg, today=today)
        if d is None:
            continue
        if d[0] == "deny":
            return d
        worst = worst or d
    return worst


def _check_segment(seg, today=None):
    if re.match(r"git\s+add\s", seg):
        tokens = seg.split()
        if "-A" in tokens or "--all" in tokens or "." in tokens:
            return (
                "deny",
                "git add -A/--all/. is forbidden (CLAUDE.md standing rules). "
                "Stage explicit paths; AGENTS.md and tests/_tmp_watchdog/ stay untracked.",
            )

    if re.match(r"python3?(\.exe)?(\s|$)", seg):
        return (
            "deny",
            "Bare python is a 0-byte stub on this machine (CLAUDE.md). "
            "Use " + MINICONDA + " instead.",
        )

    if re.match(r"git\s+push\b", seg):
        if re.search(r"(\s|=)--force\b|\s-f\b", seg):
            return (
                "deny",
                "Force push is refused by the governance guard. History rewrites "
                "are Michael's act, from his own terminal.",
            )
        return (
            "ask",
            "git push is a release act and belongs to Michael (CLAUDE.md; docs/27). "
            "Confirm that this push was explicitly delegated for this arc.",
        )

    if re.match(r"gh\s+workflow\s+run\b", seg) or re.match(r"gh\s+run\s+rerun\b", seg):
        if in_freeze(today):
            return (
                "deny",
                "Workflow dispatch during the election freeze (Constitution Article VIII, "
                "Oct 15 through Nov 10) is refused.",
            )
        return (
            "ask",
            "Workflow dispatch is a release act (CLAUDE.md; docs/27). Also check nothing "
            "is queued or in flight: a new run can displace a pending one.",
        )

    if re.match(r"gh\s+api\b", seg) and "dispatch" in seg:
        return ("ask", "Workflow dispatch via gh api is a release act (CLAUDE.md; docs/27).")

    if re.match(r"vercel\b", seg):
        return ("ask", "Deploys are release acts and belong to Michael (CLAUDE.md).")

    if in_freeze(today) and re.match(r"gh\s+(variable|secret)\b", seg):
        return (
            "deny",
            "Repository variable and secret changes during the election freeze "
            "(Constitution Article VIII) are refused.",
        )

    if re.match(r"git\s+(add|commit)\b", seg):
        low = seg.replace("\\", "/").lower()
        for tree in GENERATED_TREES:
            if tree in low:
                return (
                    "ask",
                    tree + " is generated output. It is never committed as a side effect "
                    "of local validation; confirm the work order requires it "
                    "(CLAUDE.md standing rules).",
                )

    return None


def _check_file(path, today=None):
    p = path.replace("\\", "/").lower()

    if "pipeline/prompts/" in p and not p.endswith("readme.md"):
        if in_freeze(today):
            return (
                "deny",
                "Prompt edits during the election freeze (Constitution Article VIII, "
                "Oct 15 through Nov 10) are refused.",
            )
        return (
            "ask",
            "Prompt bytes are versioned runtime behavior (docs/25 section 2). A prompt "
            "edit is a product change; confirm the work order covers it.",
        )

    if p.endswith("pipeline/config.py"):
        if in_freeze(today):
            return (
                "deny",
                "Config edits during the election freeze (Constitution Article VIII) "
                "are refused.",
            )
        return (
            "ask",
            "pipeline/config.py carries flags and thresholds. Flips are Michael's "
            "(CLAUDE.md); confirm this edit is inside the work order's scope.",
        )

    if in_freeze(today) and ".github/workflows/" in p:
        return (
            "deny",
            "Workflow edits during the election freeze (Constitution Article VIII) "
            "are refused.",
        )

    for tree in GENERATED_TREES:
        if tree in p:
            return (
                "ask",
                tree + " is generated output and is never hand-edited or regenerated "
                "as a side effect of local validation (CLAUDE.md standing rules).",
            )

    if "docs/06-constitution.md" in p:
        return (
            "ask",
            "Constitution amendments follow the Article XV process. Confirm this edit "
            "carries that authority.",
        )

    return None


def decide(tool_name, tool_input, today=None):
    """Return (decision, reason) or None. Pure function; the tests target this."""
    if tool_name in COMMAND_TOOLS:
        command = tool_input.get("command") or tool_input.get("input") or ""
        if command:
            return _check_command(command, today=today)
        return None
    if tool_name in EDIT_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if path:
            return _check_file(path, today=today)
        return None
    return None


def main():
    try:
        payload = json.load(sys.stdin)
        result = decide(payload.get("tool_name", ""), payload.get("tool_input") or {})
    except Exception as exc:  # noqa: BLE001
        print("governance_guard: failing open on internal error: " + repr(exc), file=sys.stderr)
        return 1
    if result is None:
        return 0
    decision, reason = result
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
