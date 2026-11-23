"""S74-15 Package 2: the owner's digest says what the gate means.

(a) The streak arm reads the same resolved temporal state the docs/23 section 7.3 site-current clause
names (site.reading_state), so a merely pending product day (lag 1) is green on both.
(b) The digest reports two labelled numbers: days with a published record, which the backfilled
2026-10-28..11-10 outage leaves unbroken, and ops.unattended_streak's count of consecutive clean
unattended runs, which that outage breaks. Built on the real assemble manifests read at a pinned
commit (docs/37 rule 3), written to a temporary derived tree.
"""
from __future__ import annotations

import inspect
import subprocess
import tempfile
from pathlib import Path

from pipeline import brief, config, ops, site
from tests._pinned import PIN, ROOT, pinned_bytes


def _pinned_manifests(td: Path) -> None:
    names = subprocess.run(["git", "ls-tree", "--name-only", PIN, "data/derived/manifest/"],
                           cwd=ROOT, check=True, capture_output=True, text=True).stdout.split()
    out = td / "manifest"
    out.mkdir(parents=True)
    for path in names:
        if Path(path).name.startswith("assemble-"):
            (out / Path(path).name).write_bytes(pinned_bytes(path))


def _with_derived(td: Path, fn):
    saved = config.DERIVED
    config.DERIVED = td
    try:
        return fn()
    finally:
        config.DERIVED = saved


def test_the_arm_reads_the_gate_resolution_not_a_copy_of_it():
    """docs/37 rule 1: one owner. The arm calls site.reading_state and the homepage renders through
    it; neither calls temporal_state with its own reading of the manifest."""
    assert "site.reading_state" in inspect.getsource(brief.streak)
    assert "reading_state(" in inspect.getsource(site.build_site)
    assert site.SITE_CURRENT_STATES == {"today", "latest_complete"}


def test_on_the_real_manifests_a_pending_product_day_is_green_and_the_outage_breaks_one_number():
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        _pinned_manifests(td)
        # 2026-11-21's brief: product day 11-20 is the newest published day (lag 0).
        on_time = _with_derived(td, lambda: brief.streak("2026-11-21"))
        # Remove 11-20 and 11-21: the 11-21 brief now sees a pending product day (lag 1). The old arm
        # read this RED ("no publish for 2026-11-20"); the gate calls it latest_complete.
        for d in ("2026-11-20", "2026-11-21"):
            (td / "manifest" / f"assemble-{d}.json").unlink()
        pending = _with_derived(td, lambda: brief.streak("2026-11-21"))
        # Two days pending is a miss on both.
        late = _with_derived(td, lambda: brief.streak("2026-11-22"))
        unattended = ops.unattended_streak("2026-11-21", manifest_dir=td / "manifest", limit=None)

    assert pending["status"] == "green" and pending["temporal_state"] == "latest_complete"
    assert pending["lag_days"] == 1 and pending["measured_day"] == "2026-11-19"
    assert late["status"] == "red" and late["temporal_state"] == "publication_delayed"

    # (b) the published-record count spans the outage; the unattended count breaks at it.
    assert pending["published_record_days"] >= 60
    assert unattended["days"][0] == "2026-11-11"
    assert pending["unattended_streak"] == unattended["value"] == len(unattended["days"])
    assert pending["unattended_streak"] < 15 < pending["published_record_days"]
    assert pending["unattended_since"] == "2026-11-11"
    assert "consecutive days with a published record" in pending["note"]
    assert "consecutive clean unattended runs" in pending["note"]
    assert on_time["measured_day"] == "2026-11-20"


def test_the_gate_cap_is_unchanged_by_default():
    """The section 1.4.1 gate still stops at GATE_RUNS_REQUIRED * 3; only the brief walks it all."""
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        _pinned_manifests(td)
        head = ops.unattended_streak("2026-11-21", manifest_dir=td / "manifest")
        full = ops.unattended_streak("2026-11-21", manifest_dir=td / "manifest", limit=None)
    assert head["value"] <= ops.GATE_RUNS_REQUIRED * 3 <= full["value"]
    assert head["passes"] == full["passes"]
