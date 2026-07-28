"""X7 migration evidence and quarterly restore drill tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from unittest import mock

from pipeline import build, migration_evidence, rebuild, restore_drill


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "data" / "derived" / "manifest"
COMMITTED_EVIDENCE = ROOT / "data" / "reference" / "x7-migration-manifest.json"


def test_real_committed_cycle_generates_complete_migration_evidence():
    # Against the LIVE manifests tree, so the day advances as production publishes. The invariant
    # is that a complete cycle always exists and builds well-formed evidence, never which day it
    # is: pinning the day here broke the suite the first time production moved past the recording
    # (rebase onto the 2026-07-27 data commits, found at X-validation).
    evidence = migration_evidence.build_manifest(MANIFESTS, repository_root=ROOT)
    assert evidence["production_day"] >= "2026-07-24"
    assert evidence["migration_state"] == "completed"
    assert evidence["checks"]["collect"] == {
        "degraded": False, "alerts": [], "anomalously_low": False,
    }
    assert evidence["checks"]["assemble"]["final"] is True
    assert evidence["checks"]["post"]["party_posted"] == {"D": True, "R": True}
    for stage in ("collect", "assemble", "post"):
        row = evidence["evidence"][stage]
        source = ROOT / row["path"]
        assert source.is_file()
        assert row["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_committed_migration_evidence_is_a_valid_pinned_record():
    """The committed evidence is a HISTORICAL record of the W1-W11 migration cycle. It is pinned
    to 2026-07-24 forever and is never compared against the live tree: manifests it names evolve
    legitimately (RUN C re-authenticates the post archive), and the latest complete cycle moves
    daily. Rebuilding it from the live tree and asserting byte equality made every future
    production commit a suite failure, which is how this replaced the original at X-validation."""
    data = json.loads(COMMITTED_EVIDENCE.read_text(encoding="utf-8"))
    assert data["production_day"] == "2026-07-24"
    assert data["migration_state"] == "completed"
    assert migration_evidence.canonical_bytes(data) == COMMITTED_EVIDENCE.read_bytes(), \
        "the pinned record must stay in canonical form"
    for stage in ("collect", "assemble", "post"):
        row = data["evidence"][stage]
        assert set(row) >= {"path", "sha256"}
        assert len(row["sha256"]) == 64 and int(row["sha256"], 16) >= 0
    assert data["checks"]["post"]["party_posted"] == {"D": True, "R": True}


def test_incomplete_cycle_is_not_migration_evidence():
    with tempfile.TemporaryDirectory() as temporary_name:
        root = Path(temporary_name)
        (root / "post-2026-01-01.json").write_text(json.dumps({
            "day": "2026-01-01", "posting_enabled": True, "atomic_hold": True,
            "asymmetric": False, "results": [],
        }), encoding="utf-8")
        try:
            migration_evidence.find_latest_complete_cycle(root)
            assert False, "an incomplete cycle must be rejected"
        except ValueError as error:
            assert str(error) == "no complete recorded production cycle"


def test_rebuild_report_requires_both_hashes_and_compares_bytes():
    first = "a" * 64
    second = "b" * 64
    assert restore_drill.parse_rebuild_hashes(
        f"[rebuild] derived tree hash A: {first}\n[rebuild] derived tree hash B: {second}\n"
    ) == (first, second)
    try:
        restore_drill.parse_rebuild_hashes(f"[rebuild] derived tree hash A: {first}\n")
        assert False, "one rebuild hash cannot pass"
    except ValueError:
        pass


def test_drill_verifies_assets_restores_and_reports_byte_identity():
    with tempfile.TemporaryDirectory() as temporary_name:
        temporary = Path(temporary_name)
        assets = temporary / "assets"
        assets.mkdir()
        for name in restore_drill.ASSET_NAMES:
            path = assets / name
            path.write_bytes(name.encode("ascii"))
        digest = "c" * 64
        completed = mock.Mock(returncode=0, stdout=(
            f"[rebuild] derived tree hash A: {digest}\n"
            f"[rebuild] derived tree hash B: {digest}\n"
        ), stderr="")
        with (
            mock.patch.object(restore_drill, "assert_clean_clone", return_value="f" * 40),
            mock.patch.object(restore_drill.release_provenance, "verify_sidecar", return_value=True),
            mock.patch.object(restore_drill.archive_restore, "restore_release",
                              return_value=["data/raw/congress-press/2026-07.jsonl"]),
            mock.patch.object(restore_drill.subprocess, "run", return_value=completed),
        ):
            report = restore_drill.run_drill(temporary, assets)
        assert report["clean_clone_verified"] is True
        assert report["restore"]["files_restored"] == 1
        assert report["rebuild"]["byte_identical"] is True
        assert report["rebuild"]["first_sha256"] == digest


def test_rebuild_freezes_one_real_generation_time_across_both_passes():
    calls = []
    fixed = "2026-07-27T05:00:00Z"
    with (
        mock.patch.object(rebuild.fetch, "load_mirror", return_value=[{"id": "real-record"}]),
        mock.patch.object(rebuild.deterministic, "run",
                          side_effect=lambda records, **kwargs: calls.append(kwargs)),
        mock.patch.object(rebuild, "_derived_tree_hash", side_effect=["a" * 64, "a" * 64]),
        mock.patch.object(rebuild.util, "now_utc_iso", return_value=fixed),
        mock.patch("sys.argv", ["pipeline/rebuild.py"]),
    ):
        assert rebuild.main() == 0
    assert [call["run_id"] for call in calls] == ["rebuild-A", "rebuild-B"]
    assert [call["generated_at"] for call in calls] == [fixed, fixed]


def test_timestamp_override_keeps_builder_bytes_identical():
    fixed = "2026-07-27T05:00:00Z"
    first = build.build_concordance([], {}, roster_map={}, generated_at=fixed)
    second = build.build_concordance([], {}, roster_map={}, generated_at=fixed)
    assert migration_evidence.canonical_bytes(first) == migration_evidence.canonical_bytes(second)
    first = build.build_awards([], {}, roster_map={}, generated_at=fixed, focus_day="2026-07-27")
    second = build.build_awards([], {}, roster_map={}, generated_at=fixed, focus_day="2026-07-27")
    assert migration_evidence.canonical_bytes(first) == migration_evidence.canonical_bytes(second)
