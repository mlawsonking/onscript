"""W10 acceptance tests for the gold-set harness."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from pipeline import goldset


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/w10_synthetic_annotations.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_synthetic_sample_runs_end_to_end_and_emits_full_metrics():
    result = goldset.run_synthetic(_payload())
    metrics = result["metrics"]
    assert metrics["records"] == 6
    assert set(metrics) == {
        "schema_version", "method_version", "records", "precision_by_class",
        "confusion_matrix", "family_pairwise", "party_error_gap",
    }
    assert result["adjudication"]["unresolved"] == []


def test_family_pairwise_precision_and_recall_detect_both_error_directions():
    family = goldset.run_synthetic(_payload())["metrics"]["family_pairwise"]
    assert family["true_positive_pairs"] == 1
    assert family["false_positive_pairs"] == 2
    assert family["false_negative_pairs"] == 1
    assert family["precision"] == 0.333333 and family["recall"] == 0.5


def test_date_splits_are_chronological_and_complete():
    result = goldset.run_synthetic(_payload())
    by_id = {row["candidate_id"]: row["split"] for row in result["adjudication"]["records"]}
    assert by_id == {"c1": "train", "c2": "train", "c3": "train",
                     "c4": "validation", "c5": "validation", "c6": "test"}


def test_stratified_sampling_is_deterministic_and_balanced_within_availability():
    payload = _payload()
    first = goldset.sample_candidates(payload["candidates"], 2)
    second = goldset.sample_candidates(list(reversed(payload["candidates"])), 2)
    assert first == second
    assert all(row["selected"] == min(2, row["available"]) for row in first["strata"])


def test_unresolved_disagreement_never_enters_metrics():
    payload = _payload()
    result = goldset.adjudicate(
        payload["candidates"], payload["annotations_a"], payload["annotations_b"], []
    )
    assert result["unresolved"] == [{"candidate_id": "c5", "reason": "annotation disagreement"}]
    assert all(row["candidate_id"] != "c5" for row in result["records"])


def test_documented_cli_emits_the_same_metrics():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/goldset.py"), "metrics", str(FIXTURE)],
        check=True, capture_output=True,
    )
    assert json.loads(completed.stdout) == goldset.run_synthetic(_payload())
