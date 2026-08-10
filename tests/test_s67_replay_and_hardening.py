"""S67-8 and S67-9: the replay dispatch, and the one silence that had no log line.

The replay workflow exists because the R-33.6 live shadow replay needs ANTHROPIC_API_KEY, the key
lives only in Actions secrets by design, and no workflow ever invoked scripts/shadow_replay.py
(task #218). It was prepared byte-for-byte by the Fable session on 2026-08-09 and is folded in
unchanged; what is checked here is that it parses, that it is pinned like its siblings, and that
the script it dispatches actually takes the flags it passes.
"""
from __future__ import annotations

import ast
import io
import re
from contextlib import redirect_stderr
from pathlib import Path

from pipeline import document_families


ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
REPLAY = WORKFLOWS / "replay.yml"

UPLOAD_ARTIFACT_PIN = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"


def _pins(path: Path) -> set[str]:
    return set(re.findall(r"uses:\s*(\S+@[0-9a-f]{40})", path.read_text(encoding="utf-8")))


def test_the_replay_workflow_exists_and_parses():
    assert REPLAY.exists()
    text = REPLAY.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError:                       # pragma: no cover - PyYAML is not a pipeline dep
        assert "workflow_dispatch:" in text and "jobs:" in text
        return
    document = yaml.safe_load(text)
    # PyYAML resolves the bare key `on` to the boolean True (YAML 1.1); GitHub reads the text.
    triggers = document.get("on") or document.get(True)
    assert triggers and "workflow_dispatch" in triggers
    assert "schedule" not in triggers, "the replay is an operator act, never a cron"
    assert triggers["workflow_dispatch"]["inputs"]["mode"]["options"] == ["plan", "live"]
    assert document["permissions"] == {"contents": "read"}, "the replay never writes"
    assert document["concurrency"]["group"] == "onscript-replay", (
        "the replay must not share the daily pipeline's concurrency group")


def test_every_action_is_pinned_to_the_same_shas_its_siblings_use():
    replay, collect = _pins(REPLAY), _pins(WORKFLOWS / "collect.yml")
    shared = {p for p in replay if p.split("@")[0] in {a.split("@")[0] for a in collect}}
    assert shared <= collect, f"replay pins diverge from collect.yml: {sorted(shared - collect)}"
    assert {"actions/checkout", "actions/setup-python"} <= {p.split("@")[0] for p in shared}
    assert UPLOAD_ARTIFACT_PIN in replay
    assert not re.search(r"uses:\s*\S+@(?!.{40})", REPLAY.read_text(encoding="utf-8")), (
        "an unpinned or tag-pinned action")


def test_the_live_mode_is_fail_closed_on_the_missing_secret():
    text = REPLAY.read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" in text and "refusing" in text
    assert "if: ${{ inputs.mode == 'live' }}" in text
    # The plan step must be reachable without the key, or the free gate report is unusable.
    plan = text.split("Run plan and gate progress", 1)[1].split("- name:", 1)[0]
    assert "ANTHROPIC_API_KEY" not in plan


def test_the_workflow_passes_flags_the_replay_script_actually_defines():
    """A dispatch that fails on argparse is a dispatch that failed for the wrong reason."""
    text = REPLAY.read_text(encoding="utf-8")
    used = set(re.findall(r"shadow_replay\.py ([^\n|]+)", text))
    flags = {flag for line in used for flag in re.findall(r"--[a-z-]+", line)}
    source = (ROOT / "scripts" / "shadow_replay.py").read_text(encoding="utf-8")
    defined = set(re.findall(r'add_argument\(\s*"(--[a-z-]+)"', source))
    assert flags and flags <= defined, f"undefined flags: {sorted(flags - defined)}"


def test_the_replay_never_pushes_posts_or_touches_the_pipeline_group():
    text = REPLAY.read_text(encoding="utf-8")
    for forbidden in ("git push", "post_bluesky", "POSTING_ENABLED", "onscript-pipeline",
                      "contents: write"):
        assert forbidden not in text, f"the replay workflow contains {forbidden!r}"


# --- S67-9 ------------------------------------------------------------------------------------

def test_a_missing_roster_says_out_loud_what_it_costs_the_run():
    """The roster is the only input that decides whether two offices named each other, so an
    unusable one silently disables the whole cosigned collapse and every cosigned release counts
    once PER OFFICE. That is the docs/39 C1 double count, arriving without a word."""
    log = io.StringIO()
    with redirect_stderr(log):
        result = document_families._cosigned_from_retrieval([], {}, {})
    assert result == []
    message = log.getvalue()
    assert "COSIGNED COLLAPSE DISABLED" in message
    assert "PER OFFICE" in message
    assert "roster" in message.lower()


def test_the_loud_line_does_not_fire_when_the_roster_is_usable():
    log = io.StringIO()
    with redirect_stderr(log):
        document_families._cosigned_from_retrieval([], {}, {"A000001": {"name": "Jane Doe"}})
    assert log.getvalue() == ""


def test_the_skip_is_a_log_and_not_a_raise():
    """A missing roster must not cost the day; it must only be impossible to miss in the log."""
    tree = ast.parse((ROOT / "pipeline" / "document_families.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_cosigned_from_retrieval")
    guard = next(n for n in fn.body if isinstance(n, ast.If))
    assert any(isinstance(s, ast.Return) for s in guard.body)
    assert not any(isinstance(s, ast.Raise) for s in ast.walk(guard))
