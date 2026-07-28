"""H1: the external heartbeat in watchdog.yml (Vikunja #203).

Every alerting layer OnScript has runs inside GitHub Actions, so none of them can report GitHub
Actions being down or the watchdog schedule silently ceasing to fire. The heartbeat closes that
by pinging a monitor outside GitHub, which alarms on the ping's absence.

The properties asserted here are the ones that make it safe to merge before the secret exists,
and correct once it does: it is a no-op without the secret, it fires on every run rather than
only on success, and it cannot turn the watchdog job red.
"""
from __future__ import annotations

from pathlib import Path
import re


WATCHDOG = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "watchdog.yml"


def _text() -> str:
    return WATCHDOG.read_text(encoding="utf-8")


def _step(name_fragment: str) -> str:
    """The block of one step, from its `- name:` line to the next step at the same indent."""
    text = _text()
    start = text.index(f"- name: {name_fragment}")
    rest = text[start + 1:]
    end = rest.find("\n      - name:")
    return rest if end == -1 else rest[:end]


def test_the_heartbeat_is_a_no_op_until_its_secret_exists():
    step = _step("External heartbeat")
    assert 'if [ -z "$HEALTHCHECK_PING_URL" ]; then' in step
    assert "exit 0" in step, "a missing secret must skip cleanly, never fail the probe"
    assert "HEALTHCHECK_PING_URL: ${{ secrets.HEALTHCHECK_PING_URL }}" in _text()


def test_the_heartbeat_fires_on_every_run_so_one_failure_pages_once():
    step = _step("External heartbeat")
    assert re.search(r"(?m)^\s+if: always\(\)\s*$", step), (
        "pinging only on success would page twice for one broken watchdog: the external monitor "
        "for the missing ping and the dead-man for the failure")


def test_the_heartbeat_cannot_turn_the_watchdog_red():
    step = _step("External heartbeat")
    assert "|| echo" in step, (
        "an unreachable heartbeat endpoint must not fail the job it is attached to; the monitor "
        "pages on absence anyway")


def test_the_comment_names_the_task_the_blind_spot_and_the_activation_act():
    text = _text()
    assert "#203" in text
    for phrase in ("GitHub Actions itself being down", "schedule silently"):
        assert phrase in text, f"the comment does not name the blind spot: {phrase!r}"
    assert "ACTIVATES" in text and "default branch" in text and "secret being created" in text, (
        "workflow behaviour that activates on merge plus a secret must say so where it lands")


def test_the_dead_man_still_runs_after_the_heartbeat():
    text = _text()
    assert text.index("- name: External heartbeat") < text.index("- name: Dead-man")
    dead_man = _step("Dead-man")
    assert re.search(r"(?m)^\s+if: failure\(\)\s*$", dead_man), (
        "the heartbeat must not have displaced the watchdog's own dead-man")
