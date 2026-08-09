"""S66-3 acceptance: first-carrier attribution names an office, or says so out loud.

docs/39 M1. 553 of 627 rendered phrase pages read "member name unavailable" and none named an
office. The data was never the problem: 625 of 626 committed phrase records carry a first_seen
bioguide the roster resolves. The problem was transport. data/reference/roster.json is
gitignored and reaches a job only through the state asset; RUN A and RUN B restore it, RUN C
re-rendered the whole site on a bare checkout and committed its nameless output over RUN B's
correct pages about an hour later. site.py turned the absence into `{}` with no log line, no
error, and a zero exit.

Two things are tested here. The transport chain, against the committed workflows and the live
allowlist rather than a fixture, so the missing restore step is a suite failure and not a
discovery. And the render itself: a resolvable bioguide names an office, and an unresolvable
one never renders as a raw identifier.
"""
from __future__ import annotations

import io
import re
from contextlib import redirect_stderr
from pathlib import Path

from pipeline import archive_restore, config, roster, site


WORKFLOWS = Path(config.REPO_ROOT) / ".github" / "workflows"
ROSTER_ASSET = "data/reference/roster.json"


def _workflow_text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def _workflows() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(WORKFLOWS.glob("*.yml"))}


# --- the transport chain, against the committed workflows -----------------------------------

def test_the_state_asset_packs_the_roster_in_every_workflow_that_writes_it():
    packers = {name: text for name, text in _workflows().items() if "tar -czf state.tar.gz" in text}
    assert packers, "no workflow packs the state asset any more; this check lost its subject"
    for name, text in packers.items():
        for line in text.splitlines():
            if "tar -czf state.tar.gz" in line:
                assert ROSTER_ASSET in line, f"{name} packs state without the roster: {line.strip()}"


def test_the_restore_allowlist_admits_the_roster_from_its_live_owner():
    assert ROSTER_ASSET in archive_restore.RUNTIME_REFERENCE_FILES
    assert "data/reference" in archive_restore.ARCHIVES["state.tar.gz"]


def test_every_workflow_that_renders_the_site_restores_the_state_asset():
    """The missing link. RUN C rendered and committed the site with no restore step at all."""
    offenders = []
    for name, text in _workflows().items():
        if not re.search(r"python\s+pipeline/site\.py", text):
            continue
        if "pipeline.archive_restore" not in text:
            offenders.append(name)
    assert not offenders, (
        f"these workflows render the site without restoring reference state, so every member "
        f"name in their output is 'member name unavailable': {offenders}")


def test_the_render_job_that_commits_the_site_restores_before_it_renders():
    text = _workflow_text("post.yml")
    restore = text.index("pipeline.archive_restore")
    render = text.index("python pipeline/site.py")
    commit = text.index("git add -- data/derived/manifest")
    assert restore < render < commit
    # The restore must never cost the irreversible act or the record of it.
    assert text.index("post_bluesky.py") < restore
    assert "continue-on-error: true" in text[restore - 400:restore]


# --- the render ------------------------------------------------------------------------------

def test_a_resolvable_bioguide_names_an_office_and_never_an_identifier():
    live = roster.load(allow_build=False)
    if not live:
        return  # no roster present in this checkout; the transport tests above carry the package
    bioguide = next((key for key, row in live.items()
                     if isinstance(row, dict) and row.get("name")
                     and row.get("party") and row.get("state")), None)
    assert bioguide, "the roster carries no entry with a name, party and state"
    saved = site.ROSTER
    try:
        site.ROSTER = live
        rendered = site.member_name(bioguide)
    finally:
        site.ROSTER = saved
    assert live[bioguide]["name"] in rendered
    assert f'({live[bioguide]["party"]}-{live[bioguide]["state"]})' in rendered
    assert bioguide not in rendered
    assert "member name unavailable" not in rendered


def test_an_unresolvable_bioguide_is_never_rendered_as_a_raw_identifier():
    saved = site.ROSTER
    try:
        site.ROSTER = {}
        rendered = site.member_name("Z000999")
        fallback = site.member_name("Z000999", fallback_name="Z000999")
    finally:
        site.ROSTER = saved
    assert rendered == "member name unavailable"
    assert "Z000999" not in rendered and "Z000999" not in fallback


def test_an_empty_roster_is_reported_loudly_and_never_silently():
    saved = roster.load
    log = io.StringIO()
    try:
        roster.load = lambda **_kwargs: {}
        with redirect_stderr(log):
            assert site._load_roster() == {}
    finally:
        roster.load = saved
    message = log.getvalue()
    assert "ROSTER EMPTY" in message
    assert "member name unavailable" in message
    assert "restore" in message


def test_the_render_never_rebuilds_the_roster_from_the_mirror():
    """A render that builds its own roster persists whatever it built, including nothing."""
    calls = []
    saved = roster.load
    try:
        roster.load = lambda **kwargs: calls.append(kwargs) or {"X000001": {"name": "A"}}
        site._load_roster()
    finally:
        roster.load = saved
    assert calls == [{"allow_build": False}]
