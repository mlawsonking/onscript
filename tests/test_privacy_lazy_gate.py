"""The privacy gate establishes on first use, never at import (2026-07-28 watchdog outage).

The instrument fingerprint made privacy a transitive import of ops, so the salt-less read-only
watchdog died at import time on the CI runner and the pipeline ran unwatched (its own dead-man
paged, which is how the outage was found). These tests run in SUBPROCESSES with a scrubbed
environment so they reproduce the CI runner's exact condition (docs/37 rule 2: production-shaped
tests for production paths) without poisoning this process's loaded gate state.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _saltless_env() -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in ("PRIVACY_SALT", "PRIVACY_TEST_SALT", "PRIVACY_SALT_FILE")}
    env["PRIVACY_SALT_FILE"] = str(ROOT / "tests" / "_no_such_salt_file.txt")
    return env


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([PY, "-c", code], cwd=ROOT, env=_saltless_env(),
                          capture_output=True, text=True, timeout=120)


def test_watchdog_imports_without_the_salt():
    """THE OUTAGE, pinned: `python -m pipeline.watchdog` on a runner with no salt must import.
    The watchdog is read-only and never publishes; holding the salt is not its job."""
    result = _run("import pipeline.watchdog; import pipeline.ops; print('IMPORT OK')")
    assert result.returncode == 0, f"import died: {result.stderr[-500:]}"
    assert "IMPORT OK" in result.stdout


def test_publishing_calls_still_fail_closed_without_the_salt():
    """Fail-closed is unchanged where it matters: the first gate-touching call in a salt-less
    process dies with the full remedy message. Import is free; publishing is not."""
    result = _run(
        "import pipeline.privacy as p\n"
        "try:\n"
        "    p.contains_admitted_form('some rendered text')\n"
        "except p.PrivacyGateError as e:\n"
        "    print('GATE REFUSED'); print(str(e)[:80])\n"
    )
    assert result.returncode == 0, result.stderr[-500:]
    assert "GATE REFUSED" in result.stdout
    assert "PRIVACY_SALT" in result.stdout, "the remedy message must survive the lazy path"


def test_a_wrong_salt_still_hits_the_canary_through_the_lazy_path():
    """A salt that does not match the committed form list must refuse at first use with the
    canary-mismatch message. The lazy path preserves every fail-closed branch, including the
    one that catches a diverged salt before it silently under-suppresses."""
    env = _saltless_env()
    env["PRIVACY_TEST_SALT"] = "wrong-salt-for-canary-check"
    result = subprocess.run(
        [PY, "-c",
         "import pipeline.privacy as p\n"
         "try:\n"
         "    p.is_suppressed('plain harmless text')\n"
         "except p.PrivacyGateError as e:\n"
         "    print('GATE REFUSED'); print(str(e)[:60])\n"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-500:]
    assert "GATE REFUSED" in result.stdout
    assert "canary" in result.stdout, "the canary mismatch must survive the lazy path"
