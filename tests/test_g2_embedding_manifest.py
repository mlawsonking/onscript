"""G2: the committed manifest is the only checkable claim about a store nobody can see.

The 837,040 vectors live on X: and never enter the repository, so every later statement about
them rests on this manifest. The property that matters most is therefore not that it reports a
finished run: it is that a PARTIAL run cannot read as a finished one. A manifest that rounded an
incomplete store up to complete would be a false attestation about data no reviewer can inspect.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from pipeline import util
from scripts.deep import alexandria_embed as embed
from scripts.deep import alexandria_embed_manifest as manifest


def _shard(root: Path, lane: str, congress: int, rows: int, sha: str = "a" * 64) -> None:
    paths = embed.shard_paths(lane, congress, root)
    paths["vectors"].parent.mkdir(parents=True, exist_ok=True)
    paths["vectors"].write_bytes(b"\x00" * 8)
    paths["ids"].write_text("", encoding="utf-8")
    util.write_json(paths["manifest"], {
        "rows": rows, "complete": True, "id_list_sha256": sha, "dimension": 384,
        "dtype": "float16", "model_id": embed.MODEL_ID, "model_revision": "r1",
        "wall_seconds": 1.5, "determinism_spot_check": {"rows_reencoded": 4, "max_abs_delta": 0.0},
    })


def test_a_partial_store_can_never_report_itself_complete():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        _shard(root, "press", 107, 94)
        report = manifest.collect(root)
        assert report["complete"] is False
        assert report["lanes"]["press"]["complete"] is False
        assert report["lanes"]["press"]["congresses_missing"] == list(range(108, 120))
        assert report["lanes"]["press"]["delta"] == 94 - manifest.EXPECTED_UNITS["press"]
        assert report["delta_total"] < 0


def test_a_full_shard_set_with_the_wrong_row_count_is_still_incomplete():
    """All 26 shards present is not the same claim as the right corpus being embedded."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for lane in embed.LANES:
            for congress in embed.CONGRESSES:
                _shard(root, lane, congress, 1)
        report = manifest.collect(root)
        assert report["lanes"]["press"]["congresses_missing"] == []
        assert report["lanes"]["press"]["complete"] is False, (
            "every shard present but the wrong total must not read as complete")
        assert report["complete"] is False


def test_the_manifest_reconciles_against_the_docs34_precondition_counts():
    assert manifest.GATE_UNITS == {"press": 684853, "crec": 152187}
    assert sum(manifest.GATE_UNITS.values()) == 837040
    with tempfile.TemporaryDirectory() as raw:
        report = manifest.collect(Path(raw))
        assert report["gate_total"] == 837040
        assert "684,853" in report["reconciliation_basis"]
        assert report["reconciliation_command"].endswith("alexandria_stage2_verify.py")


def test_the_out_of_scope_sliver_is_named_and_subtracted_rather_than_absorbed():
    """A documented exclusion of 15 rows and an unexplained shortfall of 15 rows look identical.

    docs/34 section 1 records 15 CREC rows dated to congress 106, outside the 107-119 pass. If
    the manifest simply expected 152,187 those rows would show as a permanent unexplained delta,
    and a reader would learn to ignore a non-zero delta. If it silently expected 152,172 the
    exclusion would be invisible. It carries both numbers and the reason.
    """
    assert manifest.OUT_OF_SCOPE["crec"] == {"congress_106_boundary_sliver": 15}
    assert manifest.EXPECTED_UNITS["crec"] == 152187 - 15
    assert manifest.EXPECTED_UNITS["press"] == 684853
    with tempfile.TemporaryDirectory() as raw:
        report = manifest.collect(Path(raw))
        crec = report["lanes"]["crec"]
        assert crec["gate_units"] == 152187
        assert crec["expected_units"] == 152172
        assert crec["out_of_scope_units"] == {"congress_106_boundary_sliver": 15}
        assert "congress 106" in report["reconciliation_basis"]


def test_the_manifest_carries_model_identity_content_hashes_and_a_resume_command():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        _shard(root, "press", 107, 94, sha="b" * 64)
        report = manifest.collect(root)
        assert report["model"]["id"] == [embed.MODEL_ID]
        assert report["model"]["revision"] == ["r1"]
        assert report["model"]["dimension"] == [384]
        assert report["model"]["storage_dtype"] == ["float16"]
        assert report["model"]["compute_dtype"] == embed.COMPUTE_DTYPE
        shard = report["lanes"]["press"]["shards"][0]
        assert shard["id_list_sha256"] == "b" * 64
        assert shard["wall_seconds"] == 1.5
        assert "alexandria_embed.py" in report["resume_command"]
        assert report["determinism_worst_max_abs_delta"] == 0.0


def test_an_interrupted_shard_is_reported_missing_not_counted():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        paths = embed.shard_paths("press", 107, root)
        paths["vectors"].parent.mkdir(parents=True, exist_ok=True)
        paths["vectors"].write_bytes(b"\x00")
        paths["ids"].write_text("", encoding="utf-8")
        util.write_json(paths["manifest"], {"rows": 94, "complete": False,
                                            "id_list_sha256": "c" * 64})
        report = manifest.collect(root)
        assert report["lanes"]["press"]["rows"] == 0
        assert 107 in report["lanes"]["press"]["congresses_missing"]


def test_the_committed_manifest_is_a_valid_pinned_record():
    """Validated as itself, never re-derived from the live store.

    The store is a Release-scale artifact on X: that not every checkout has, and it grows as the
    pass resumes. Asserting the committed manifest equals a fresh collect would fail on any box
    without the drive and on this one the moment the run advances (docs/37 rule 3).
    """
    path = (Path(__file__).resolve().parent.parent / "data" / "reference"
            / "alexandria-embeddings-manifest.json")
    if not path.is_file():
        return
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["method_version"] == manifest.METHOD_VERSION
    assert record["gate_total"] == 837040
    assert record["expected_total"] == 837040 - sum(
        sum(counts.values()) for counts in manifest.OUT_OF_SCOPE.values())
    assert record["model"]["id"] == [embed.MODEL_ID]
    assert isinstance(record["complete"], bool)
    for lane, summary in record["lanes"].items():
        assert lane in embed.LANES
        assert summary["rows"] == sum(shard["rows"] for shard in summary["shards"])
        assert summary["delta"] == summary["rows"] - summary["expected_units"]
        assert summary["complete"] == (not summary["congresses_missing"]
                                       and summary["delta"] == 0)
    assert record["rows_total"] == sum(lane["rows"] for lane in record["lanes"].values())
